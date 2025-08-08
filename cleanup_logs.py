#!/usr/bin/env python3

import argparse
import os
import sys
import shutil
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Set

IS_WINDOWS = os.name == "nt"

try:
    if IS_WINDOWS:
        import msvcrt  # type: ignore
except Exception:
    msvcrt = None  # type: ignore


@dataclass
class TargetSpec:
    name: str
    files: List[Path] = field(default_factory=list)
    directories: List[Path] = field(default_factory=list)
    # Globs or extensions to consider when doing age-based pruning inside directories
    prune_extensions: Set[str] = field(default_factory=lambda: {".log", ".csv", ".md", ".json", ".txt"})


# Central source of truth for what gets cleaned
TARGETS: Dict[str, TargetSpec] = {
    "equity": TargetSpec(name="equity", files=[Path("logs/equity.csv")]),
    "trades": TargetSpec(name="trades", files=[Path("logs/trades.csv")]),
    "rejected": TargetSpec(name="rejected", files=[Path("logs/rejected_trades.csv")]),
    "cache": TargetSpec(name="cache", files=[Path("logs/research_cache.json")]),
    "coingecko": TargetSpec(name="coingecko", files=[Path("logs/coingecko_cache.json")]),
    "report": TargetSpec(name="report", files=[Path("logs/daily_research_report.md")]),
    "thesis": TargetSpec(name="thesis", files=[Path("logs/thesis_log.md")]),
    "sched_logs": TargetSpec(name="sched_logs", files=[Path("logs/scheduler_multiagent.log"), Path("logs/scheduler.log")]),
    "transcripts": TargetSpec(name="transcripts", directories=[Path("logs/agent_transcripts")]),
    "prompts": TargetSpec(name="prompts", directories=[Path("logs/prompts")]),
}

# Alias "all" to include every defined target
ALL_TARGET_KEYS = list(TARGETS.keys())


@dataclass
class Resolution:
    files_to_delete: List[Path] = field(default_factory=list)
    dirs_to_delete: List[Path] = field(default_factory=list)  # only for full delete (no retention)
    locked_files: List[Path] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Safely clean ChatGPT-Kraken-Bot logs and caches. Dry-run by default. "
            "Stop the bot (scheduler_multiagent.py) before executing."
        )
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Select all known log targets",
    )
    parser.add_argument(
        "--targets",
        type=str,
        default=None,
        help=(
            "Comma-separated list of targets to clean. Options: "
            + ", ".join(sorted(ALL_TARGET_KEYS))
        ),
    )
    parser.add_argument(
        "--older-than",
        type=int,
        default=None,
        help="Only delete files older than N days. Directories are pruned by age (not removed).",
    )
    parser.add_argument(
        "--backup",
        type=str,
        default=None,
        help="Zip backup file path to create before deletion (of selected artifacts).",
    )
    parser.add_argument(
        "--check-locks",
        action="store_true",
        help="Attempt to detect locked files (best-effort; Windows only). Locked files are skipped.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print each action for files/dirs.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Perform deletion. If not provided, runs in dry-run mode.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip interactive confirmation when --execute is used (CI usage).",
    )
    return parser.parse_args()


def resolve_selection(args: argparse.Namespace) -> List[str]:
    if args.all:
        return list(ALL_TARGET_KEYS)
    if args.targets:
        requested = [t.strip().lower() for t in args.targets.split(",") if t.strip()]
        unknown = [t for t in requested if t not in TARGETS]
        if unknown:
            print(f"Unknown targets: {', '.join(unknown)}")
            print(f"Valid targets: {', '.join(sorted(ALL_TARGET_KEYS))}")
            sys.exit(2)
        return requested
    # Default to all in dry-run, but explicit is clearer: show all
    return list(ALL_TARGET_KEYS)


def is_file_locked(path: Path) -> bool:
    if not IS_WINDOWS or msvcrt is None:
        return False  # Best-effort: skip lock detection on non-Windows
    try:
        # Try to open and acquire a non-blocking exclusive lock on at least 1 byte
        with open(path, "a+b") as f:
            size = max(1, path.stat().st_size if path.exists() else 1)
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, size)
                # Immediately release
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, size)
                return False
            except OSError:
                return True
    except Exception:
        # If open fails due to permissions or other errors, treat as not locked; deletion may still fail and be reported
        return False


def collect_targets(
    selected: List[str], older_than_days: int | None, check_locks: bool, verbose: bool
) -> Resolution:
    res = Resolution()
    cutoff_time = None
    if older_than_days is not None and older_than_days >= 0:
        cutoff_time = datetime.now() - timedelta(days=older_than_days)

    # Helper to consider age
    def is_older(path: Path) -> bool:
        if cutoff_time is None:
            return True
        try:
            ctime = datetime.fromtimestamp(path.stat().st_mtime)
            return ctime < cutoff_time
        except FileNotFoundError:
            return False

    # Files from each target
    for key in selected:
        spec = TARGETS[key]
        # Files
        for f in spec.files:
            if f.exists() and is_older(f):
                if check_locks and is_file_locked(f):
                    res.locked_files.append(f)
                else:
                    res.files_to_delete.append(f)
            elif verbose:
                print(f"SKIP (missing or too new): {f}")

        # Directories
        for d in spec.directories:
            if not d.exists():
                if verbose:
                    print(f"SKIP (missing dir): {d}")
                continue

            if cutoff_time is None:
                # Full directory removal
                res.dirs_to_delete.append(d)
            else:
                # Age-based pruning inside directory
                for path in d.rglob("*"):
                    if path.is_file():
                        if spec.prune_extensions and path.suffix.lower() not in spec.prune_extensions:
                            continue
                        if is_older(path):
                            if check_locks and is_file_locked(path):
                                res.locked_files.append(path)
                            else:
                                res.files_to_delete.append(path)

    # Deduplicate while preserving order
    def dedup(paths: List[Path]) -> List[Path]:
        seen: Set[Path] = set()
        out: List[Path] = []
        for p in paths:
            if p not in seen:
                seen.add(p)
                out.append(p)
        return out

    res.files_to_delete = dedup(res.files_to_delete)
    res.dirs_to_delete = dedup(res.dirs_to_delete)
    res.locked_files = dedup(res.locked_files)
    return res


def ensure_logs_structure_exists():
    Path("logs/agent_transcripts").mkdir(parents=True, exist_ok=True)
    Path("logs/prompts").mkdir(parents=True, exist_ok=True)


def create_backup_zip(zip_path: Path, files: List[Path], dirs: List[Path], older_than_days: int | None, verbose: bool):
    # If user provided a directory as zip path, construct filename
    if zip_path.exists() and zip_path.is_dir():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = zip_path / f"logs_backup_{ts}.zip"
    else:
        # Ensure directory exists
        zip_path.parent.mkdir(parents=True, exist_ok=True)

    # Avoid overwriting existing zip by appending timestamp
    if zip_path.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = zip_path.with_name(zip_path.stem + f"_{ts}" + zip_path.suffix)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        base = Path.cwd()
        # Add files explicitly resolved
        for f in files:
            if f.exists():
                try:
                    zf.write(f, arcname=f.relative_to(base))
                    if verbose:
                        print(f"BACKUP FILE: {f}")
                except Exception as e:
                    print(f"Failed to backup file {f}: {e}")
        # Add directories (full if not retention; if retention active, skip since files already added)
        if older_than_days is None:
            for d in dirs:
                if d.exists():
                    for path in d.rglob("*"):
                        if path.is_file():
                            try:
                                zf.write(path, arcname=path.relative_to(base))
                                if verbose:
                                    print(f"BACKUP FILE: {path}")
                            except Exception as e:
                                print(f"Failed to backup file {path}: {e}")
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"Backup created: {zip_path} ({size_mb:.2f} MB)")


def on_rm_error(func, path, exc_info):
    # Attempt to chmod and retry for Windows read-only files
    try:
        os.chmod(path, 0o666)
        func(path)
    except Exception:
        pass


def perform_deletion(res: Resolution, verbose: bool) -> Tuple[int, int, int, int]:
    deleted = 0
    skipped = 0
    failed = 0
    locked = len(res.locked_files)

    # Files first
    for f in res.files_to_delete:
        try:
            f.unlink()
            deleted += 1
            if verbose:
                print(f"DELETED FILE: {f}")
        except FileNotFoundError:
            skipped += 1
            if verbose:
                print(f"SKIP (missing): {f}")
        except Exception as e:
            failed += 1
            print(f"FAILED to delete file {f}: {e}")

    # Directories
    for d in res.dirs_to_delete:
        try:
            shutil.rmtree(d, onerror=on_rm_error)
            deleted += 1
            if verbose:
                print(f"DELETED DIRECTORY: {d}")
        except FileNotFoundError:
            skipped += 1
            if verbose:
                print(f"SKIP (missing dir): {d}")
        except Exception as e:
            failed += 1
            print(f"FAILED to delete directory {d}: {e}")

    return deleted, skipped, failed, locked


def print_preview(res: Resolution):
    print("")
    print("========== CLEANUP PREVIEW (dry-run) ==========")
    print(f"Files to delete: {len(res.files_to_delete)}")
    print(f"Directories to delete: {len(res.dirs_to_delete)}")
    if res.locked_files:
        print(f"Locked files (will be skipped): {len(res.locked_files)}")
        for p in res.locked_files[:10]:
            print(f"  [LOCKED] {p}")
        if len(res.locked_files) > 10:
            print(f"  ... and {len(res.locked_files) - 10} more")
    print("==============================================")
    print("")


def confirmation_prompt(total_items: int) -> bool:
    print("WARNING: This will permanently delete selected logs and caches.")
    print("Ensure the bot (scheduler_multiagent.py) is NOT running.")
    print(f"About to delete up to {total_items} items. This cannot be undone.")
    resp = input('Type YES to proceed: ').strip()
    return resp == "YES"


def main():
    args = parse_args()

    # Intro warning
    print("\n== ChatGPT-Kraken-Bot Log Cleanup ==\n")
    print("Targets managed in this script include: agent transcripts, prompts, equity/trades CSVs, research caches, scheduler logs, thesis, CoinGecko cache, research report.")

    selected = resolve_selection(args)

    res = collect_targets(selected, args.older_than, args.check_locks, args.verbose)

    # Preview
    print_preview(res)

    # Backup if requested
    if args.backup:
        zip_path = Path(args.backup)
        try:
            create_backup_zip(zip_path, res.files_to_delete, res.dirs_to_delete, args.older_than, args.verbose)
        except Exception as e:
            print(f"Backup failed: {e}")
            # Proceed with caution; user chose backup so warn
            print("Proceeding without backup.")

    # Dry-run by default
    if not args.execute:
        print("Dry-run complete. No files were deleted.")
        print("To perform deletion, re-run with --execute (and optionally --force).")
        return 0

    total_to_delete = len(res.files_to_delete) + len(res.dirs_to_delete)
    if total_to_delete == 0 and len(res.locked_files) == 0:
        print("Nothing to delete.")
        ensure_logs_structure_exists()
        print("Fresh structure ensured for logs/agent_transcripts and logs/prompts.")
        return 0

    # Confirmation unless forced
    if not args.force:
        if not confirmation_prompt(total_to_delete):
            print("Aborted. No changes made.")
            return 1

    deleted, skipped, failed, locked = perform_deletion(res, args.verbose)

    # Re-create base directories for clean first run
    ensure_logs_structure_exists()

    # Summary
    print("")
    print("========== CLEANUP SUMMARY ==========")
    print(f"Deleted: {deleted}")
    print(f"Skipped (missing/too-new): {skipped}")
    if locked:
        print(f"Locked (skipped): {locked}")
    print(f"Failed: {failed}")
    print("=====================================")

    if failed > 0:
        print("One or more deletions failed. Check permissions or stop any process locking files.")
        return 2

    print("Fresh start ready. You can now run the bot.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
