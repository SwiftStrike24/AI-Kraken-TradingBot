import logging
import sys
import os
from rich.logging import RichHandler

# --- Emoji toggle (auto-detect) ---
USE_EMOJI = True
# Disable by env override
if os.getenv("LOG_EMOJI", "1") in {"0", "false", "False"}:
    USE_EMOJI = False
# Disable if stdout encoding is not utf
enc = getattr(sys.stdout, "encoding", None)
if enc and "utf" not in enc.lower():
    USE_EMOJI = False
# Disable on Windows legacy consoles without UTF-8
if os.name == "nt" and not USE_EMOJI:
    USE_EMOJI = False

# --- Constants for Emojis and Colors ---
LOG_LEVELS = {
    "DEBUG": {"emoji": "🐛", "fallback": "DBG", "color": "cyan"},
    "INFO": {"emoji": "✅", "fallback": "INF", "color": "green"},
    "WARNING": {"emoji": "⚠️ ", "fallback": "WRN", "color": "yellow"},
    "ERROR": {"emoji": "❌", "fallback": "ERR", "color": "red"},
    "CRITICAL": {"emoji": "🔥", "fallback": "CRT", "color": "bold red"},
}

class CustomRichHandler(RichHandler):
    """Custom RichHandler to add emojis to log levels."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def render_message(self, record: logging.LogRecord, message: str) -> str:
        """Render the message with a level-specific emoji and agent name."""
        level_info = LOG_LEVELS.get(record.levelname, {"emoji": "➡️", "fallback": "»", "color": "white"})
        emoji = level_info["emoji"] if USE_EMOJI else level_info.get("fallback", "")
        
        # Format agent name from logger name
        agent_name_full = record.name
        if agent_name_full == "__main__":
            agent_name = "Scheduler"
        elif agent_name_full.startswith('agents.'):
            agent_name = agent_name_full.split('.')[1].replace('_', '-').upper()
        elif agent_name_full.startswith('bot.'):
            agent_name = agent_name_full.split('.')[1].replace('_', '-').upper()
        else:
            agent_name = record.name.upper()

        # Prepend emoji and agent name to the log message
        prefix = f"{emoji} " if emoji else ""
        record.msg = f"{prefix}[{agent_name}] {record.msg}"
        return super().render_message(record, message)

def setup_colored_logging():
    """
    Sets up a beautiful, colored logger using the rich library.
    
    This function configures the root logger to output structured, colored logs
    to the console, making it easier to distinguish between different log levels
    and messages.
    """
    # Configure the root logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",  # Basic format, RichHandler will do the heavy lifting
        datefmt="[%X]",
        handlers=[
            CustomRichHandler(
                rich_tracebacks=True, 
                tracebacks_show_locals=True,
                show_path=False,
                log_time_format="[%Y-%m-%d %H:%M:%S]"
            )
        ]
    )
    
    # Get the root logger
    log = logging.getLogger("rich")
    # Advertise emoji mode once at startup
    mode = "enabled" if USE_EMOJI else "disabled"
    logging.getLogger(__name__).info(f"Logging emojis {mode} (encoding={enc})")
    return log

def get_logger(name: str):
    """
    Returns a logger instance for a specific module.
    
    Args:
        name: The name of the logger (usually __name__)
        
    Returns:
        A logger instance
    """
    return logging.getLogger(name)

# --- Example Usage ---
if __name__ == "__main__":
    setup_colored_logging()
    
    logger = get_logger(__name__)
    
    logger.debug("This is a debug message for detailed tracing.")
    logger.info("The process completed successfully.")
    logger.warning("The API returned an unexpected but non-fatal value.")
    logger.error("A recoverable error occurred. Retrying operation.")
    logger.critical("A critical, non-recoverable error occurred. System shutting down.")
    
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("An exception was caught.")
