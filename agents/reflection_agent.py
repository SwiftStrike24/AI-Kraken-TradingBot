"""
Reflection Agent (Historical Analyst)

This agent is responsible for acting as the bot's long-term memory. It analyzes
past performance, decisions, and cognitive processes to generate a "Reflection Report"
that informs the current trading cycle. This allows the bot to learn from its
own history and avoid repeating mistakes.
"""

import os
import logging
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

from .base_agent import BaseAgent

# --- CONFIGURATION ---
TRANSCRIPT_SESSIONS_TO_ANALYZE = 1 # The number of recent, non-empty session folders to analyze

class ReflectionAgent(BaseAgent):
    """
    The Reflection-AI analyzes historical data to provide long-term context.
    
    This agent:
    1. Reads historical logs (trades, equity, theses, transcripts)
    2. Synthesizes the data to identify patterns and learnings
    3. Produces a concise "Reflection Report" for the Strategist-AI
    """
    
    def __init__(self, logs_dir: str = "logs", session_dir: str = None):
        """
        Initialize the Reflection Agent.
        
        Args:
            logs_dir: Directory for reading historical logs
            session_dir: Optional session directory for unified transcript storage
        """
        super().__init__("Reflection-AI", logs_dir, session_dir)
        
        # Define paths for all historical data sources
        self.equity_log_path = os.path.join(logs_dir, "equity.csv")
        self.trades_log_path = os.path.join(logs_dir, "trades.csv")
        self.rejected_trades_log_path = os.path.join(logs_dir, "rejected_trades.csv")
        self.thesis_log_path = os.path.join(logs_dir, "thesis_log.md")
        self.transcript_archive_dir = os.path.join(logs_dir, "agent_transcripts")
        
        # Reflection template path
        self.reflection_template_path = os.path.join("bot", "reflection_prompt_template.md")
        
        # Lazy Gemini client import (to avoid hard dependency if not configured)
        self._gemini = None
        
        # Simple in-memory cache for this process
        self._cache_key = None
        self._cache_value = None
        
        self.logger.info("Reflection Agent initialized. Ready to analyze history.")

    def _parse_iso8601_utc(self, series: pd.Series) -> pd.Series:
        """Parse ISO8601 strings (with optional fractional seconds) into UTC timestamps, vectorized.
        Falls back gracefully if pandas lacks ISO8601 fast-path support.
        """
        try:
            # Pandas 2.0+: fast ISO8601 path
            parsed = pd.to_datetime(series, format="ISO8601", utc=True, errors="coerce")
        except TypeError:
            # Fallback: generic parser with dateutil
            parsed = pd.to_datetime(series, utc=True, errors="coerce")
        return parsed

    def _get_gemini_client(self):
        if self._gemini is None:
            from bot.gemini_client import GeminiClient
            self._gemini = GeminiClient()
        return self._gemini

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the historical analysis and reflection process.
        
        Args:
            inputs: Supervisor directives (e.g., how many days to look back)
            
        Returns:
            A dictionary containing the structured "Reflection Report".
        """
        self.logger.info("Starting historical reflection process...")
        
        try:
            lookback_days = inputs.get('reflection_lookback_days', 3)
            
            # 1. Analyze performance trends from equity log
            performance_analysis = self._analyze_performance_trends(lookback_days)
            
            # 2. Analyze trade patterns from trades log
            trade_patterns = self._analyze_trade_patterns(lookback_days)
            
            # 3. Analyze past strategic theses
            thesis_evolution = self._analyze_thesis_evolution(lookback_days)
            
            # 4. (bounded) Analyze cognitive history from agent transcripts
            cognitive_history = self._analyze_agent_transcripts()

            # 5. Synthesize via Gemini for long-context reasoning
            reflection_report = self._synthesize_with_gemini(
                performance_analysis,
                trade_patterns,
                thesis_evolution,
                cognitive_history
            )
            
            self.logger.info("Historical reflection process completed.")
            
            return {
                "status": "success",
                "agent": "Reflection-AI",
                "reflection_report": reflection_report,
                "data_sources_analyzed": ["equity.csv", "trades.csv", "thesis_log.md", "agent_transcripts"]
            }
        except Exception as e:
            self.logger.error(f"Failed to generate reflection report: {e}", exc_info=True)
            return {
                "status": "error",
                "agent": "Reflection-AI",
                "error_message": str(e),
                "reflection_report": self._generate_placeholder_report() # Fallback
            }

    def _analyze_performance_trends(self, lookback_days: int) -> Dict[str, Any]:
        """Analyzes equity.csv to identify performance trends."""
        if not os.path.exists(self.equity_log_path):
            return {"summary": "No equity data available to analyze performance."}
        
        try:
            equity_df = pd.read_csv(self.equity_log_path, names=['timestamp', 'total_equity_usd'])
            equity_df['timestamp'] = self._parse_iso8601_utc(equity_df['timestamp'])
            equity_df['total_equity_usd'] = pd.to_numeric(equity_df['total_equity_usd'], errors='coerce')
            equity_df = equity_df.dropna(subset=['timestamp'])
            equity_df = equity_df.dropna(subset=['total_equity_usd'])
            parsed_count = len(equity_df)
            self.logger.debug(f"Equity timestamps parsed (UTC): {parsed_count} rows")
            if parsed_count:
                self.logger.debug(f"Equity time range: {equity_df['timestamp'].min()} → {equity_df['timestamp'].max()}")
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
            self.logger.debug(f"Equity cutoff (UTC): {cutoff_date}")
            recent_equity = equity_df[equity_df['timestamp'] > cutoff_date]
            
            if len(recent_equity) < 2:
                return {"summary": "Not enough recent equity data to analyze performance trends."}

            start_equity = recent_equity.iloc[0]['total_equity_usd']
            end_equity = recent_equity.iloc[-1]['total_equity_usd']
            if pd.isna(start_equity) or pd.isna(end_equity):
                return {"summary": "Equity data contains non-numeric values; skipping performance trend."}
            change_pct = ((end_equity - start_equity) / start_equity) * 100 if start_equity > 0 else 0
            
            trend = "profitable" if change_pct > 0 else "unprofitable"
            summary = f"Over the last {lookback_days} days, the portfolio has been {trend}, with a net change of {change_pct:.2f}%."
            
            return {"summary": summary, "change_pct": change_pct}
        except Exception as e:
            self.logger.warning(f"Could not analyze equity log: {e}")
            return {"summary": "Error analyzing equity log."}

    def _analyze_trade_patterns(self, lookback_days: int) -> Dict[str, Any]:
        """Analyzes trades.csv to identify patterns in trading behavior."""
        if not os.path.exists(self.trades_log_path):
            return {"summary": "No trade data available to analyze patterns."}

        try:
            trades_df = pd.read_csv(self.trades_log_path)
            trades_df['timestamp'] = self._parse_iso8601_utc(trades_df['timestamp'])
            trades_df = trades_df.dropna(subset=['timestamp'])
            self.logger.debug(f"Trades timestamps parsed (UTC): {len(trades_df)} rows")
            if not trades_df.empty:
                self.logger.debug(f"Trades time range: {trades_df['timestamp'].min()} → {trades_df['timestamp'].max()}")

            cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
            self.logger.debug(f"Trades cutoff (UTC): {cutoff_date}")
            recent_trades = trades_df[trades_df['timestamp'] > cutoff_date]
            
            if recent_trades.empty:
                return {"summary": "No trades were executed in the last few days."}

            most_traded_asset = recent_trades['pair'].mode()[0] if not recent_trades['pair'].empty else "None"
            action_counts = recent_trades['action'].value_counts()
            buy_count = action_counts.get('buy', 0)
            sell_count = action_counts.get('sell', 0)

            summary = f"Trading activity in the last {lookback_days} days shows {len(recent_trades)} trades, primarily focusing on {most_traded_asset}. Actions were {buy_count} buys and {sell_count} sells."
            return {"summary": summary, "most_traded": most_traded_asset, "trade_count": len(recent_trades)}
        except Exception as e:
            self.logger.warning(f"Could not analyze trade log: {e}")
            return {"summary": "Error analyzing trade log."}

    def _analyze_thesis_evolution(self, lookback_days: int) -> Dict[str, Any]:
        """Analyzes thesis_log.md to track strategic shifts."""
        if not os.path.exists(self.thesis_log_path):
            return {"summary": "No thesis log available to analyze strategic evolution."}
        
        try:
            with open(self.thesis_log_path, 'r', encoding='utf-8') as f:
                content = f.read()

            theses = [t.strip() for t in content.split('---') if t.strip()]
            if not theses:
                return {"summary": "Thesis log is empty."}
            
            last_thesis = theses[-1]
            # Simple heuristic for change
            if "altcoin rotation" in last_thesis.lower():
                trend = "a shift towards altcoin rotation"
            elif "momentum trading" in last_thesis.lower():
                trend = "a focus on momentum trading"
            elif "defensive holding" in last_thesis.lower():
                trend = "a move to a defensive holding strategy"
            else:
                trend = "a consistent strategic approach"

            summary = f"The most recent strategic thesis indicates {trend}."
            return {"summary": summary, "last_thesis_preview": last_thesis[:150] + "..."}
        except Exception as e:
            self.logger.warning(f"Could not analyze thesis log: {e}")
            return {"summary": "Error analyzing thesis log."}

    def _analyze_agent_transcripts(self) -> Dict[str, Any]:
        """
        Finds the most recent, non-empty session folders and extracts their content
        to provide bounded cognitive history for reflection (not passed downstream).
        """
        if not os.path.exists(self.transcript_archive_dir):
            return {"summary": "No agent transcripts available for analysis.", "full_text": ""}

        try:
            # Get all daily directories (e.g., '2025-08-06')
            daily_dirs = sorted([d for d in os.listdir(self.transcript_archive_dir) if os.path.isdir(os.path.join(self.transcript_archive_dir, d))], reverse=True)
            
            collected_sessions_content = []
            sessions_found = 0

            for day in daily_dirs:
                day_path = os.path.join(self.transcript_archive_dir, day)
                # Get all session directories for that day (e.g., '20-58-54')
                session_dirs = sorted([s for s in os.listdir(day_path) if os.path.isdir(os.path.join(day_path, s))], reverse=True)

                for session in session_dirs:
                    if sessions_found >= TRANSCRIPT_SESSIONS_TO_ANALYZE:
                        break
                    
                    session_path = os.path.join(day_path, session)
                    files = [f for f in os.listdir(session_path) if f.endswith('.md')]
                    if not files:
                        continue
                        
                    session_content = f"\n\n--- REFLECTION ON SESSION: {day} {session} ---\n"
                    processed = 0
                    for file_name in sorted(files):
                        if processed >= 6:  # bound per-session excerpts
                            break
                        try:
                            with open(os.path.join(session_path, file_name), 'r', encoding='utf-8') as f:
                                text = f.read()
                                # keep only first 2000 chars per file for prompt control
                                session_content += f"\n--- TRANSCRIPT: {file_name} ---\n" + text[:2000]
                                processed += 1
                        except Exception as e:
                            self.logger.warning(f"Could not read transcript file {file_name}: {e}")
                    
                    collected_sessions_content.append(session_content)
                    sessions_found += 1
                
                if sessions_found >= TRANSCRIPT_SESSIONS_TO_ANALYZE:
                    break
            
            if not collected_sessions_content:
                return {"summary": "No recent, non-empty agent transcripts found.", "full_text": ""}

            full_text = "\n".join(collected_sessions_content)
            summary = f"Analyzed the cognitive transcripts of the last {sessions_found} trading cycles."
            
            return {"summary": summary, "full_text": full_text}
            
        except Exception as e:
            self.logger.error(f"Error analyzing agent transcripts: {e}", exc_info=True)
            return {"summary": "An error occurred during transcript analysis.", "full_text": ""}

    def _synthesize_with_gemini(self, performance: dict, trades: dict, thesis: dict, cognition: dict) -> Dict[str, Any]:
        """Use Gemini 2.5 Pro to produce a concise reflection JSON, then adapt to our downstream schema."""
        try:
            # Cache guard: reuse result if inputs haven't changed in this process run
            import hashlib
            base_str = "|".join([
                performance.get('summary', ''),
                trades.get('summary', ''),
                thesis.get('summary', ''),
                cognition.get('summary', ''),
                str(len(cognition.get('full_text', '')))
            ])
            cache_key = hashlib.sha256(base_str.encode('utf-8')).hexdigest()
            if self._cache_key == cache_key and self._cache_value is not None:
                self.logger.info("Using cached reflection synthesis result (inputs unchanged)")
                return self._cache_value

            # Load template
            with open(self.reflection_template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            system = self._extract_between(template, '<SYSTEM>', '</SYSTEM>')
            # Build input blocks (compact where possible)
            performance_block = performance.get('summary', '')
            trades_block = trades.get('summary', '')
            thesis_block = thesis.get('summary', '')
            transcripts_block = cognition.get('full_text', '')

            prompt = template.replace('{performance_block}', performance_block)
            prompt = prompt.replace('{trades_block}', trades_block)
            prompt = prompt.replace('{thesis_block}', thesis_block)
            prompt = prompt.replace('{transcripts_block}', transcripts_block)

            client = self._get_gemini_client()
            gemini_json = client.generate_json(system=system, prompt=prompt)

            # If empty/error, retry once without transcripts to avoid safety/length blocks
            if not isinstance(gemini_json, dict) or ("error" in gemini_json) or (not gemini_json.get('summary_250w') and not gemini_json.get('what_worked') and not gemini_json.get('raw_text')):
                self.logger.warning("Gemini returned empty/error; retrying reflection synthesis without transcripts block")
                prompt_no_tx = template.replace('{performance_block}', performance_block)
                prompt_no_tx = prompt_no_tx.replace('{trades_block}', trades_block)
                prompt_no_tx = prompt_no_tx.replace('{thesis_block}', thesis_block)
                prompt_no_tx = prompt_no_tx.replace('{transcripts_block}', "[omitted]")
                gemini_json = client.generate_json(system=system, prompt=prompt_no_tx)

            # Adapt to strategist-friendly shape
            summary_text = gemini_json.get('summary_250w', '') if isinstance(gemini_json, dict) else ''
            # Create lean reflection to avoid bloating downstream prompts
            lean = {
                "summary": summary_text or f"{performance.get('summary','')} {trades.get('summary','')} {thesis.get('summary','')} {cognition.get('summary','')}",
                "key_learnings": [
                    item for item in [
                        gemini_json.get('what_worked', '') if isinstance(gemini_json, dict) else '',
                        gemini_json.get('what_failed', '') if isinstance(gemini_json, dict) else '',
                        gemini_json.get('guardrails', '') if isinstance(gemini_json, dict) else ''
                    ] if item
                ],
                "recommended_focus": gemini_json.get('actionable_rules', '') if isinstance(gemini_json, dict) else "Use actionable patterns and guardrails from reflection."
            }
            # Store cache
            self._cache_key = cache_key
            self._cache_value = lean
            return lean
        except Exception as e:
            self.logger.warning(f"Gemini synthesis failed, falling back to heuristic: {e}")
            return self._synthesize_reflection_report(performance, trades, thesis, cognition)

    def _extract_between(self, text: str, start_tag: str, end_tag: str) -> str:
        try:
            s = text.index(start_tag) + len(start_tag)
            e = text.index(end_tag, s)
            return text[s:e].strip()
        except ValueError:
            return "You are a senior crypto quantitative coach. Return strict JSON only."

    def _synthesize_reflection_report(self, performance: dict, trades: dict, thesis: dict, cognition: dict) -> Dict[str, Any]:
        """Heuristic synthesis fallback (legacy)."""
        summary = f"{performance.get('summary', '')} {trades.get('summary', '')} {thesis.get('summary', '')} {cognition.get('summary', '')}"
        key_learnings = []
        if "unprofitable" in performance.get('summary', ''):
            key_learnings.append("Recent performance has been negative; re-evaluate the current strategy.")
        elif "profitable" in performance.get('summary', ''):
            key_learnings.append("The current strategy has been profitable; consider maintaining or doubling down.")
        if trades.get('trade_count', 0) > 10:
            key_learnings.append(f"High trading frequency noted. Most traded asset was {trades.get('most_traded')}.")
        if "defensive" in thesis.get('summary', ''):
            key_learnings.append("Strategy has recently shifted to be more defensive and risk-averse.")
        if not key_learnings:
            key_learnings.append("No strong patterns detected in recent activity.")
        return {
            "summary": summary,
            "key_learnings": key_learnings,
            "recommended_focus": "Based on historical data, the AI should carefully consider if the current strategy is still optimal given its recent performance."
        }

    def _generate_placeholder_report(self) -> Dict[str, Any]:
        """Generates a placeholder reflection report for demonstration."""
        return {
            "summary": "Historical analysis indicates a pattern of success when holding high-conviction assets like ETH through short-term volatility. Past attempts to trade low-volume altcoins have resulted in minor losses. The last cycle's defensive hold was profitable.",
            "key_learnings": [
                "Patience with core assets (ETH, BTC) is often rewarded.",
                "Avoid trades below 5% of portfolio value due to minimum order size rejections.",
                "Macro news (e.g., Fed announcements) has had a significant impact on profitability."
            ],
            "recommended_focus": "Consider holding ETH if market conditions are volatile but fundamentals remain strong. Prioritize trades in assets with proven liquidity and strong narratives."
        }

    def generate_reasoning(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> str:
        """
        Generate a natural language explanation of the reflection process.
        """
        report = outputs.get("reflection_report", {})
        
        reasoning = f"""
        Historical Reflection Analysis:
        
        1. Data Synthesis: Analyzed historical data from sources: {outputs.get('data_sources_analyzed', [])}.
        2. Pattern Recognition: Identified key patterns in past trading performance and AI decision-making.
        3. Learning Extraction: Synthesized findings into actionable learnings, such as '{report.get('key_learnings', [])[0] if report.get('key_learnings') else 'N/A'}'.
        4. Strategic Recommendation: Provided a strategic focus based on these learnings: '{report.get('recommended_focus', '')}'.
        
        The generated Reflection Report provides essential long-term memory to the system, enabling it to learn from past cycles and improve its strategic decision-making.
        """
        return reasoning.strip()
