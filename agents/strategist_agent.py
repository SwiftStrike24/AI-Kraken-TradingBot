"""
Strategist Agent (Prompt Engineering Specialist)

This agent specializes in building sophisticated, contextual prompts for the AI trading engine.
It combines market intelligence, portfolio state, and historical performance into optimized
prompts that maximize the quality of trading decisions.

This replaces the monolithic prompt_engine.py with a more cognitive, transparent approach.
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

import pandas as pd

from .base_agent import BaseAgent
from bot.kraken_api import KrakenAPI
from bot.prompt_engine import PromptEngine, PromptEngineError

# logger = logging.getLogger(__name__)

class StrategistAgent(BaseAgent):
    """
    The Strategist-AI specializes in prompt engineering and context assembly.
    
    This agent:
    1. Receives market intelligence from the Analyst-AI
    2. Gathers current portfolio state and historical performance
    3. Constructs optimized prompts using advanced prompt engineering techniques
    4. Provides ready-to-execute prompt payloads to the Trader-AI
    """
    
    def __init__(self, kraken_api: KrakenAPI, logs_dir: str = "logs", session_dir: str = None):
        """
        Initialize the Strategist Agent.
        
        Args:
            kraken_api: Kraken API instance for portfolio data
            logs_dir: Directory for saving agent transcripts
            session_dir: Optional session directory for unified transcript storage
        """
        super().__init__("Strategist-AI", logs_dir, session_dir)
        
        self.kraken_api = kraken_api
        
        # Initialize the advanced prompt engine
        try:
            self.prompt_engine = PromptEngine()
            self.logger.info("Advanced prompt engine initialized successfully")
        except PromptEngineError as e:
            self.logger.error(f"Failed to initialize prompt engine: {e}")
            raise
        
        # Define paths for historical data
        self.thesis_log_path = os.path.join(logs_dir, "thesis_log.md")
        self.equity_log_path = os.path.join(logs_dir, "equity.csv")
        self.trades_log_path = os.path.join(logs_dir, "trades.csv")
        self.rejected_trades_log_path = os.path.join(logs_dir, "rejected_trades.csv")
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute prompt construction and strategy formulation.
        
        Args:
            inputs: Contains market intelligence report from Analyst-AI and supervisor directives
            
        Returns:
            Structured prompt payload ready for AI execution
        """
        self.logger.info("Beginning strategic prompt construction...")
        
        try:
            # Extract the market intelligence report and CoinGecko data
            reflection_report = inputs.get('reflection_report', {})
            research_report = inputs.get('research_report', {})
            coingecko_data = inputs.get('coingecko_data', {})
            trending_data = inputs.get('trending_data', {})
            supervisor_directives = inputs.get('supervisor_directives', {})
            
            # Gather portfolio context
            portfolio_context = self.get_portfolio_context()
            
            # Gather historical performance context
            performance_context = self._gather_performance_context()
            
            # (NEW) Analyze the performance of the last trade cycle
            performance_context['last_cycle_analysis'] = self._analyze_last_trade_cycle()

            # (NEW) Gather feedback on previously rejected trades
            rejected_trades_context = self._gather_rejected_trades_context()

            # Gather thesis history
            thesis_context = self._gather_thesis_context()
            
            # Gather trading rules from Kraken
            trading_rules = self._gather_trading_rules()
            
            # --- NEW (Phase 2): Get refinement context if it exists ---
            refinement_context = inputs.get('refinement_context', None)
            
            # Construct the optimized prompt using the advanced prompt engine
            prompt_payload = self._construct_prompt_payload(
                reflection_report,
                research_report, 
                coingecko_data,
                trending_data,
                portfolio_context, 
                performance_context, 
                thesis_context,
                trading_rules,
                supervisor_directives,
                rejected_trades_context, # Pass new context
                refinement_context # Pass refinement context
            )
            
            self.logger.info("Strategic prompt construction completed successfully")
            
            return {
                "status": "success",
                "agent": "Strategist-AI",
                "timestamp": datetime.now().isoformat(),
                "prompt_payload": prompt_payload,
                "research_report_summary": self._summarize_research(research_report),
                "portfolio_summary": self._summarize_portfolio(portfolio_context),
                "strategy_confidence": self._assess_strategy_confidence(prompt_payload),
                "prompt_quality_metrics": self._assess_prompt_quality(prompt_payload)
            }
            
        except Exception as e:
            self.logger.error(f"Strategic prompt construction failed: {e}")
            raise
    
    def get_portfolio_context(self) -> dict:
        """
        Gather current portfolio state and balance information using live Kraken API data.
        
        Returns:
            Comprehensive portfolio context data including USD values and allocations
        """
        try:
            # Get comprehensive portfolio data from Kraken API (always live, never assume)
            portfolio_data = self.kraken_api.get_comprehensive_portfolio_context()
            
            self.logger.info(f"Live portfolio retrieved: Total equity ${portfolio_data['total_equity']:,.2f}")
            self.logger.info(f"Current holdings: {list(portfolio_data['raw_balances'].keys())}")
            
            # Convert to format expected by strategist logic
            holdings = []
            for asset, value_data in portfolio_data['usd_values'].items():
                if asset != 'USD' and value_data['value'] > 0:  # Exclude USD cash from holdings list
                    holdings.append({
                        'asset': asset,
                        'amount': value_data['amount'],
                        'usd_price': value_data['price'],
                        'usd_value': value_data['value'],
                        'allocation_pct': portfolio_data['allocation_percentages'].get(asset, 0)
                    })
            
            return {
                "status": "active" if portfolio_data['total_equity'] > 0 else "empty",
                "cash_balance": portfolio_data['cash_balance'],
                "holdings": holdings,
                "total_positions": len(holdings),
                "total_equity": portfolio_data['total_equity'],
                "allocation_percentages": portfolio_data['allocation_percentages'],
                "tradeable_assets": portfolio_data['tradeable_assets'],
                "crypto_value": portfolio_data['crypto_value'],
                "raw_portfolio_data": portfolio_data  # Full data for advanced analysis
            }
            
        except Exception as e:
            self.logger.error(f"Failed to gather portfolio context: {e}")
            return {
                "status": "error",
                "error_message": str(e),
                "cash_balance": 0.0,
                "holdings": [],
                "total_positions": 0,
                "total_equity": 0.0,
                "allocation_percentages": {},
                "tradeable_assets": [],
                "crypto_value": 0.0,
                "raw_portfolio_data": {}
            }
    
    def _analyze_last_trade_cycle(self) -> Dict[str, Any]:
        """
        Analyzes the profitability of the trades executed since the last thesis was logged.
        This creates the core of the performance feedback loop.

        Returns:
            A dictionary containing the analysis summary.
        """
        try:
            if not os.path.exists(self.trades_log_path) or not os.path.exists(self.equity_log_path):
                return {"status": "no_data", "summary": "Log files not found for performance analysis."}

            trades_df = pd.read_csv(self.trades_log_path)
            equity_df = pd.read_csv(self.equity_log_path, names=['timestamp', 'total_equity_usd'])

            # --- BUG FIX: Definitive Timestamp Handling ---
            # Convert all timestamps to timezone-aware UTC.
            # The `utc=True` parameter correctly handles both timezone-aware strings (like in trades.csv)
            # and naive strings (like in equity.csv), converting everything to a consistent UTC format.
            trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'], errors='coerce', utc=True)
            equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'], errors='coerce', utc=True)

            # Find the timestamp of the last thesis
            last_thesis_time = self._get_last_thesis_timestamp()
            if last_thesis_time is None:
                return {"status": "no_thesis", "summary": "No previous thesis to analyze."}

            # Filter trades and equity data since the last thesis
            recent_trades = trades_df[trades_df['timestamp'] > last_thesis_time]
            relevant_equity = equity_df[equity_df['timestamp'] > last_thesis_time]

            if recent_trades.empty:
                return {"status": "no_trades", "summary": "No trades were executed in the last cycle to analyze."}

            # Calculate PnL for the cycle
            if not relevant_equity.empty:
                start_equity = equity_df[equity_df['timestamp'] <= last_thesis_time].iloc[-1]['total_equity_usd']
                end_equity = relevant_equity.iloc[-1]['total_equity_usd']
                pnl_usd = end_equity - start_equity
                pnl_percent = (pnl_usd / start_equity) * 100 if start_equity != 0 else 0
                summary = f"The last trade cycle resulted in a PnL of ${pnl_usd:,.2f} ({pnl_percent:+.2f}%)."
            else:
                pnl_usd = 0
                pnl_percent = 0
                summary = "Could not calculate PnL for the last cycle due to missing equity data."

            return {
                "status": "analyzed",
                "summary": summary,
                "pnl_usd": pnl_usd,
                "pnl_percent": pnl_percent,
                "trade_count": len(recent_trades)
            }

        except FileNotFoundError:
            return {"status": "no_data", "summary": "Log files not found for performance analysis."}
        except Exception as e:
            self.logger.error(f"Failed to analyze last trade cycle: {e}")
            return {"status": "error", "summary": f"An error occurred during performance analysis: {e}"}

    def _gather_rejected_trades_context(self) -> str:
        """
        Reads the rejected_trades.csv log and creates a summary for the AI.
        This forms a feedback loop to teach the AI about invalid trade plans.
        """
        try:
            if not os.path.exists(self.rejected_trades_log_path):
                return "No rejected trades from the previous cycle to review."

            rejected_df = pd.read_csv(self.rejected_trades_log_path)
            if rejected_df.empty:
                return "No rejected trades from the previous cycle to review."

            # Get rejections from the last 24 hours
            rejected_df['timestamp'] = pd.to_datetime(rejected_df['timestamp'], errors='coerce', utc=True)
            last_24_hours = datetime.now(pd.Timestamp.utcnow().tz) - timedelta(hours=24)
            recent_rejections = rejected_df[rejected_df['timestamp'] > last_24_hours]

            if recent_rejections.empty:
                return "No rejected trades from the previous cycle to review."

            summary_parts = ["The following trades were proposed but REJECTED by the validation system. Do NOT make these same mistakes again:"]
            for _, row in recent_rejections.iterrows():
                reason = row.get('rejection_reason', 'No reason specified')
                pair = row.get('requested_pair', 'N/A')
                allocation = row.get('allocation_percentage', 'N/A')
                summary_parts.append(f"- Trade for {pair} at {allocation:.1f}% allocation failed because: '{reason}'.")
            
            summary_parts.append("\nRevise your strategy to ensure all proposed trades are valid according to the provided TRADING_RULES.")
            return "\n".join(summary_parts)

        except Exception as e:
            self.logger.error(f"Failed to gather rejected trades context: {e}")
            return "Could not analyze rejected trades due to an error."

    def _get_last_thesis_timestamp(self) -> Optional[datetime]:
        """Helper to get the timestamp of the last thesis entry."""
        if not os.path.exists(self.thesis_log_path):
            return None
        with open(self.thesis_log_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        theses = content.split('---')
        if len(theses) < 2: # Need at least one full entry
            return None
            
        # The second to last entry is the most recent complete one
        last_thesis_block = theses[-2] 
        timestamp_line = last_thesis_block.strip().split('\n')[0]
        
        try:
            # E.g., "## Thesis for 2025-H2 03:25:42 UTC"
            timestamp_str = timestamp_line.replace("## Thesis for ", "").replace(" UTC", "")
            # Convert to timezone-aware UTC datetime for consistent comparison
            return pd.to_datetime(timestamp_str, utc=True)
        except (ValueError, IndexError):
            return None


    def _gather_performance_context(self) -> Dict[str, Any]:
        """
        Gather historical performance data and trends.
        
        Returns:
            Performance context for strategy formulation
        """
        try:
            if not os.path.exists(self.equity_log_path):
                return {
                    "status": "no_history",
                    "total_return": 0.0,
                    "days_active": 0,
                    "trend": "unknown"
                }
            
            # Read the equity log (CSV has no headers: timestamp, total_equity_usd)
            equity_df = pd.read_csv(self.equity_log_path, names=['timestamp', 'total_equity_usd'])
            
            if len(equity_df) < 2:
                return {
                    "status": "insufficient_history",
                    "total_return": 0.0,
                    "days_active": len(equity_df),
                    "trend": "unknown"
                }
            
            # Calculate performance metrics
            initial_equity = equity_df.iloc[0]['total_equity_usd']
            current_equity = equity_df.iloc[-1]['total_equity_usd']
            total_return = ((current_equity - initial_equity) / initial_equity) * 100
            
            # Calculate recent trend (last 7 days or available data)
            recent_data = equity_df.tail(min(7, len(equity_df)))
            if len(recent_data) >= 2:
                recent_start = recent_data.iloc[0]['total_equity_usd']
                recent_end = recent_data.iloc[-1]['total_equity_usd']
                recent_trend = "improving" if recent_end > recent_start else "declining" if recent_end < recent_start else "stable"
            else:
                recent_trend = "unknown"
            
            return {
                "status": "available",
                "initial_equity": initial_equity,
                "current_equity": current_equity,
                "total_return": round(total_return, 2),
                "days_active": len(equity_df),
                "recent_trend": recent_trend,
                "performance_quality": "strong" if total_return > 5 else "moderate" if total_return > 0 else "weak"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to gather performance context: {e}")
            return {
                "status": "error",
                "error_message": str(e),
                "total_return": 0.0,
                "days_active": 0,
                "trend": "unknown"
            }
    
    def _gather_thesis_context(self) -> Dict[str, Any]:
        """
        Gather the most recent strategic thesis for continuity.
        
        Returns:
            Context about the current strategic thesis
        """
        try:
            if not os.path.exists(self.thesis_log_path):
                return {
                    "status": "no_thesis",
                    "last_thesis": "",
                    "thesis_age_days": 0
                }
            
            with open(self.thesis_log_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the most recent thesis
            theses = content.split('---')
            if theses:
                last_thesis = theses[-1].strip()
                
                # Extract thesis summary (first 200 chars for context)
                thesis_summary = last_thesis[:200] + "..." if len(last_thesis) > 200 else last_thesis
                
                return {
                    "status": "available",
                    "last_thesis": thesis_summary,
                    "thesis_age_days": 1,  # Simplified - could calculate actual age
                    "thesis_length": len(last_thesis)
                }
            else:
                return {
                    "status": "empty",
                    "last_thesis": "",
                    "thesis_age_days": 0
                }
                
        except Exception as e:
            self.logger.error(f"Failed to gather thesis context: {e}")
            return {
                "status": "error",
                "error_message": str(e),
                "last_thesis": "",
                "thesis_age_days": 0
            }
    
    def _gather_trading_rules(self) -> str:
        """
        Gather trading rules and constraints from Kraken, format for AI consumption.
        Includes dynamic minimum order size warnings based on current portfolio size.
        
        Returns:
            Formatted trading rules string for prompt injection.
        """
        try:
            # Get all USD trading pairs with their minimum order sizes
            usd_pairs = self.kraken_api.get_all_usd_trading_rules()
            
            if not usd_pairs:
                return "⚠️ WARNING: No USD trading pairs available from Kraken API."
            
            # Format the trading rules for AI consumption
            rules_text = "VALID KRAKEN USD TRADING PAIRS & MINIMUM ORDER SIZES:\n\n"
            
            # Sort pairs by base asset for better readability
            sorted_pairs = sorted(usd_pairs.items(), key=lambda x: x[1]['base'])
            
            for pair_name, pair_info in sorted_pairs:
                base_asset = pair_info['base']
                ordermin = float(pair_info['ordermin'])
                
                # Clean base asset name for display
                clean_base = base_asset[1:] if base_asset.startswith(('X', 'Z')) and len(base_asset) > 1 else base_asset
                
                rules_text += f"✅ {pair_name} ({clean_base}/USD)\n"
                rules_text += f"   - Minimum order size: {ordermin:.8f} {clean_base}\n"
                rules_text += f"   - Use exact pair name: '{pair_name}'\n\n"
            
            rules_text += "\n🚨 CRITICAL TRADING REQUIREMENTS:\n"
            rules_text += "1. Use ONLY the exact pair names listed above (e.g., 'XETHZUSD', not 'ETHUSD')\n"
            rules_text += "2. Ensure your trade volume meets the minimum order size for each pair\n"
            rules_text += "3. Calculate trade volume: (allocation_percentage × portfolio_value) ÷ asset_price\n"
            rules_text += "4. If calculated volume < ordermin, either increase allocation or skip the trade\n"
            rules_text += "5. PORTFOLIO REBALANCING: You can sell ANY asset you currently hold to free up capital\n"
            rules_text += "6. SELLING STRATEGY: To rebalance from Asset A to Asset B, sell allocation_percentage of Asset A, then buy Asset B\n"
            rules_text += "7. NO CASH CONSTRAINTS: Even with limited cash, you can sell existing positions to fund new trades\n"
            # Add dynamic minimum order size warnings based on portfolio size
            try:
                # Reuse portfolio context if already computed in this execution
                try:
                    if 'cached_portfolio_context' in getattr(self, '__dict__', {}):
                        portfolio_context = self.__dict__['cached_portfolio_context']
                    else:
                        portfolio_context = self.get_portfolio_context()
                        self.__dict__['cached_portfolio_context'] = portfolio_context
                except Exception:
                    portfolio_context = self.get_portfolio_context()
                portfolio_value = portfolio_context.get('total_equity', 0)
                
                rules_text += "\n⚠️ MINIMUM ORDER SIZE AWARENESS:\n"
                rules_text += f"Current portfolio value: ${portfolio_value:.2f}\n"
                
                if portfolio_value < 50:
                    rules_text += "⚠️ SMALL PORTFOLIO WARNING: Be extremely careful with minimum order sizes!\n"
                    rules_text += "- XRP requires minimum 2.0 XRP (~$6.00) = {:.1f}% of your portfolio\n".format(6.00/portfolio_value*100 if portfolio_value > 0 else 0)
                    rules_text += "- ETH requires minimum 0.002 ETH (~$7.00) = {:.1f}% of your portfolio\n".format(7.00/portfolio_value*100 if portfolio_value > 0 else 0)
                    rules_text += "- BTC requires minimum 0.00005 BTC (~$5.50) = {:.1f}% of your portfolio\n".format(5.50/portfolio_value*100 if portfolio_value > 0 else 0)
                    rules_text += "- Consider avoiding assets where minimum order exceeds 15% of portfolio\n"
                else:
                    rules_text += "For your portfolio size, most minimum order requirements should be manageable.\n"
                    rules_text += "- XRP minimum: 2.0 XRP (~$6.00)\n"
                    rules_text += "- ETH minimum: 0.002 ETH (~$7.00)\n"
                    rules_text += "- BTC minimum: 0.00005 BTC (~$5.50)\n"
                rules_text += "\n"
                
            except Exception as e:
                # Fallback to static warnings if portfolio data unavailable
                rules_text += "\n⚠️ MINIMUM ORDER SIZE AWARENESS:\n"
                rules_text += "Be careful with minimum order sizes - check portfolio value vs. minimums\n"
                rules_text += "- XRP requires minimum 2.0 XRP (~$6.00)\n"
                rules_text += "- ETH requires minimum 0.002 ETH (~$7.00)\n"
                rules_text += "- BTC requires minimum 0.00005 BTC (~$5.50)\n\n"
            
            rules_text += f"📊 Total tradeable pairs: {len(usd_pairs)}\n"
            rules_text += f"🔄 Rules updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            
            return rules_text
            
        except Exception as e:
            self.logger.error(f"Failed to gather trading rules: {e}")
            return f"❌ ERROR: Could not fetch trading rules from Kraken API: {str(e)}"
    
    def _construct_prompt_payload(self, reflection_report: Dict[str, Any], research_report: Dict[str, Any], 
                                coingecko_data: Dict[str, Any],
                                trending_data: Dict[str, Any], portfolio_context: Dict[str, Any], 
                                performance_context: Dict[str, Any], thesis_context: Dict[str, Any],
                                trading_rules: Dict[str, Any], supervisor_directives: Dict[str, Any],
                                rejected_trades_context: str, refinement_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Construct the final prompt payload using the advanced prompt engine.
        
        Args:
            reflection_report: Historical analysis from Reflection-AI
            research_report: Market intelligence from Analyst-AI
            coingecko_data: Market data from CoinGecko-AI
            trending_data: Trending tokens data from CoinGecko-AI
            portfolio_context: Current portfolio state
            performance_context: Historical performance data
            thesis_context: Previous strategic thesis
            trading_rules: Trading rules and constraints from Kraken
            supervisor_directives: Any special directives from the Supervisor-AI
            rejected_trades_context: Feedback on previously rejected trades
            refinement_context: Specific feedback for the current refinement loop
            
        Returns:
            Complete prompt payload ready for AI execution
        """
        try:
            # Convert reflection report to text format
            reflection_text = self._convert_reflection_to_text(reflection_report)

            # Convert research report to text format for the prompt engine
            research_text = self._convert_research_to_text(research_report)
            
            # Convert portfolio context to text format
            portfolio_text = self._convert_portfolio_to_text(portfolio_context)
            
            # Convert CoinGecko data to text format
            coingecko_text = self._convert_coingecko_to_text(coingecko_data, trending_data)
            
            # Build the prompt using the advanced prompt engine
            prompt_text = self.prompt_engine.build_prompt(
                portfolio_context=portfolio_text,
                research_report=research_text,
                last_thesis=thesis_context.get('last_thesis', ''),
                coingecko_data=coingecko_text,
                trading_rules=trading_rules, # Pass formatted trading rules to the prompt engine
                performance_review=performance_context.get('last_cycle_analysis', {}).get('summary', 'No analysis available.'),
                rejected_trades_review=rejected_trades_context,
                historical_reflection=reflection_text, # Pass new reflection context
                refinement_context=refinement_context
            )
            
            return {
                "prompt_text": prompt_text,
                "estimated_tokens": len(prompt_text.split()) * 1.3,  # Rough token estimate
                "research_summary": self._extract_research_summary(research_report),
                "portfolio_summary": self._extract_portfolio_summary(portfolio_context),
                "performance_summary": self._extract_performance_summary(performance_context),
                "strategic_focus": supervisor_directives.get('strategic_focus', 'balanced_growth'),
                "risk_parameters": supervisor_directives.get('risk_parameters', 'standard'),
                "construction_timestamp": datetime.now().isoformat()
            }
            
        except PromptEngineError as e:
            self.logger.error(f"Prompt engine failed: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Prompt construction failed: {e}")
            raise

    def _convert_reflection_to_text(self, reflection_report: Dict[str, Any]) -> str:
        """Convert structured reflection report to text format for prompt engine."""
        if not reflection_report or not reflection_report.get('summary'):
            return "No historical reflection available for this cycle."

        summary = reflection_report.get('summary', 'No summary available.')
        learnings = reflection_report.get('key_learnings', [])
        focus = reflection_report.get('recommended_focus', 'No specific focus recommended.')

        text_parts = [f"**Executive Summary:** {summary}\n"]
        
        if learnings:
            text_parts.append("**Key Learnings from Past Cycles:**")
            for learning in learnings:
                text_parts.append(f"- {learning}")
            text_parts.append("")

        text_parts.append(f"**Recommended Focus for this Cycle:** {focus}")
        
        return "\n".join(text_parts)

    def _convert_research_to_text(self, research_report: Dict[str, Any]) -> str:
        """Convert structured research report back to text format for prompt engine."""
        if not research_report:
            return "No market intelligence available."
        
        # Reconstruct the report in markdown format
        text_parts = ["# Daily Market Research Report\n"]
        
        # Add crypto headlines
        crypto_headlines = research_report.get('crypto_headlines', [])
        if crypto_headlines:
            text_parts.append("## 📰 Crypto News Headlines")
            for headline in crypto_headlines:
                text_parts.append(f"- {headline}")
            text_parts.append("")
        
        # Add macro updates
        macro_updates = research_report.get('macro_updates', [])
        if macro_updates:
            text_parts.append("## 🏛️ Macro & Regulatory Updates")
            for update in macro_updates:
                text_parts.append(f"- {update}")
            text_parts.append("")
        
        # Add market context
        market_context = research_report.get('market_context', '')
        if market_context:
            text_parts.append("## 📊 Market Context")
            text_parts.append(f"- {market_context}")
            text_parts.append("")
        
        # Add sentiment analysis
        sentiment = research_report.get('sentiment_analysis', {})
        if sentiment:
            text_parts.append("## 🔍 Market Sentiment Analysis")
            text_parts.append(f"- Overall sentiment: {sentiment.get('sentiment', 'neutral')} (confidence: {sentiment.get('confidence', 0)*100:.0f}%)")
            text_parts.append(f"- Analysis: {sentiment.get('reasoning', 'No analysis available')}")
            text_parts.append("")
        
        return "\n".join(text_parts)
    
    def _convert_portfolio_to_text(self, portfolio_context: Dict[str, Any]) -> str:
        """Convert structured portfolio context to text format for prompt engine."""
        if portfolio_context.get('status') == 'empty':
            return "Portfolio is currently empty. Cash on hand: $0.00 USD."
        
        if portfolio_context.get('status') == 'error':
            return f"Portfolio data unavailable due to error: {portfolio_context.get('error_message', 'unknown error')}"
        
        # Build comprehensive portfolio description
        cash_balance = portfolio_context.get('cash_balance', 0)
        total_equity = portfolio_context.get('total_equity', 0)
        
        text_parts = [f"Current cash balance: ${cash_balance:.2f} USD."]
        text_parts.append(f"Total portfolio value: ${total_equity:.2f} USD.")
        
        holdings = portfolio_context.get('holdings', [])
        if holdings:
            text_parts.append("Current Holdings:")
            for holding in holdings:
                asset = holding['asset']
                amount = holding['amount']
                usd_value = holding['usd_value']
                usd_price = holding['usd_price']
                allocation_pct = holding.get('allocation_pct', 0)
                
                text_parts.append(f"- {asset}: {amount:.6f} (Value: ${usd_value:.2f} @ ${usd_price:.2f}) [{allocation_pct:.1f}% of portfolio]")
            
            # Add trading capabilities context
            text_parts.append("")
            text_parts.append("TRADING OPPORTUNITIES:")
            text_parts.append("- You can SELL any current holdings to reallocate capital")
            text_parts.append("- You can BUY new positions using available cash or proceeds from sales")
            text_parts.append("- Current positions are NOT locked - you can rebalance as needed")
            
            if cash_balance < 1.0:
                text_parts.append(f"- Limited cash (${cash_balance:.2f}) available, but you can sell existing positions to fund new trades")
            
        else:
            text_parts.append("No crypto assets held.")
        
        return "\n".join(text_parts)
    
    def _convert_coingecko_to_text(self, coingecko_data: Dict[str, Any], trending_data: Dict[str, Any]) -> str:
        """
        Convert CoinGecko market data to text format for prompt injection.
        
        Args:
            coingecko_data: Market data from CoinGecko API
            trending_data: Trending tokens data from CoinGecko API
            
        Returns:
            Formatted text suitable for prompt injection
        """
        text_parts = []
        
        if coingecko_data:
            text_parts.append("## Real-Time Market Data (CoinGecko)")
            text_parts.append("")
            
            # Format major tokens data
            for token_id, data in coingecko_data.items():
                name = data.get('name', token_id)
                symbol = data.get('symbol', '').upper()
                price = data.get('current_price', 0)
                market_cap_rank = data.get('market_cap_rank', 'N/A')
                
                # Price changes
                change_1h = data.get('price_change_percentage_1h', 0) or 0
                change_24h = data.get('price_change_percentage_24h', 0) or 0
                change_7d = data.get('price_change_percentage_7d', 0) or 0
                
                # Format market cap and volume
                market_cap = data.get('market_cap', 0)
                volume_24h = data.get('total_volume', 0)
                
                text_parts.append(f"**{name} ({symbol})**")
                text_parts.append(f"  Price: ${price:,.2f} | Rank: #{market_cap_rank}")
                text_parts.append(f"  Changes: 1h {change_1h:+.1f}% | 24h {change_24h:+.1f}% | 7d {change_7d:+.1f}%")
                if market_cap and volume_24h:
                    text_parts.append(f"  Market Cap: ${market_cap:,.0f} | Volume 24h: ${volume_24h:,.0f}")
                text_parts.append("")
        
        if trending_data and trending_data.get('coins'):
            text_parts.append("## Trending Tokens")
            text_parts.append("")
            
            trending_coins = trending_data.get('coins', [])[:5]  # Top 5 trending
            for i, coin in enumerate(trending_coins, 1):
                name = coin.get('name', 'Unknown')
                symbol = coin.get('symbol', '').upper()
                rank = coin.get('market_cap_rank', 'N/A')
                price_btc = coin.get('price_btc', 0)
                
                text_parts.append(f"{i}. {name} ({symbol}) - Rank #{rank} | {price_btc:.8f} BTC")
            
            text_parts.append("")
        
        # Add market overview if we have multiple tokens
        if len(coingecko_data) >= 2:
            text_parts.append("## Market Overview")
            text_parts.append("")
            
            # Calculate average 24h change for major tokens
            changes_24h = [data.get('price_change_percentage_24h', 0) or 0 for data in coingecko_data.values()]
            avg_change = sum(changes_24h) / len(changes_24h) if changes_24h else 0
            
            if avg_change > 2:
                market_tone = "bullish"
            elif avg_change < -2:
                market_tone = "bearish"
            else:
                market_tone = "neutral"
            
            text_parts.append(f"Market tone: {market_tone} (avg 24h change: {avg_change:+.1f}%)")
            text_parts.append("")
        
        return "\n".join(text_parts) if text_parts else "No real-time market data available."
    
    def _extract_research_summary(self, research_report: Dict[str, Any]) -> str:
        """Extract a concise summary of the research report."""
        if not research_report:
            return "No research data available"
        
        sentiment = research_report.get('sentiment_analysis', {}).get('sentiment', 'neutral')
        headline_count = len(research_report.get('crypto_headlines', [])) + len(research_report.get('macro_updates', []))
        key_themes = research_report.get('key_themes', [])[:3]  # Top 3 themes
        
        theme_names = [theme.get('theme', '') for theme in key_themes if isinstance(theme, dict)]
        
        return f"Market sentiment: {sentiment}, {headline_count} headlines analyzed, key themes: {', '.join(theme_names)}"
    
    def _extract_portfolio_summary(self, portfolio_context: Dict[str, Any]) -> str:
        """Extract a concise summary of the portfolio state."""
        if portfolio_context.get('status') != 'active':
            return f"Portfolio status: {portfolio_context.get('status', 'unknown')}"
        
        cash = portfolio_context.get('cash_balance', 0)
        positions = portfolio_context.get('total_positions', 0)
        total_value = portfolio_context.get('total_equity', 0)
        
        return f"${total_value:.2f} total value, {positions} positions, ${cash:.2f} cash ({portfolio_context.get('allocation_percentages', {}).get('USD', 0):.1f}%)"
    
    def _extract_performance_summary(self, performance_context: Dict[str, Any]) -> str:
        """Extract a concise summary of performance data."""
        if performance_context.get('status') not in ['available']:
            return f"Performance data: {performance_context.get('status', 'unknown')}"
        
        total_return = performance_context.get('total_return', 0)
        days_active = performance_context.get('days_active', 0)
        trend = performance_context.get('recent_trend', 'unknown')
        
        return f"{total_return:+.1f}% total return over {days_active} days, recent trend: {trend}"
    
    def _summarize_research(self, research_report: Dict[str, Any]) -> Dict[str, Any]:
        """Create a structured summary of the research report."""
        return {
            "headline_count": len(research_report.get('crypto_headlines', [])) + len(research_report.get('macro_updates', [])),
            "sentiment": research_report.get('sentiment_analysis', {}).get('sentiment', 'neutral'),
            "confidence": research_report.get('sentiment_analysis', {}).get('confidence', 0.0),
            "top_themes": [theme.get('theme', '') for theme in research_report.get('key_themes', [])[:5]]
        }
    
    def _summarize_portfolio(self, portfolio_context: Dict[str, Any]) -> Dict[str, Any]:
        """Create a structured summary of the portfolio."""
        return {
            "status": portfolio_context.get('status', 'unknown'),
            "total_value": portfolio_context.get('total_equity', 0),
            "position_count": portfolio_context.get('total_positions', 0),
            "cash_percentage": portfolio_context.get('allocation_percentages', {}).get('USD', 0),
            "assets": [h.get('asset', '') for h in portfolio_context.get('holdings', [])]
        }
    
    def _assess_strategy_confidence(self, prompt_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Assess confidence in the strategy formulation."""
        # Base confidence on data availability and quality
        research_summary = prompt_payload.get('research_summary', '')
        portfolio_summary = prompt_payload.get('portfolio_summary', '')
        
        confidence_score = 0.5  # Base confidence
        
        # Boost confidence based on data quality
        # Extract headline count from research summary (format: "Market sentiment: X, Y headlines analyzed, ...")
        try:
            if 'headlines analyzed' in research_summary:
                # Find the number before "headlines analyzed"
                parts = research_summary.split('headlines analyzed')[0].split()
                headline_count = int(parts[-1])
                if headline_count > 10:
                    confidence_score += 0.2
        except (ValueError, IndexError):
            # If parsing fails, continue without boost
            pass
        
        if 'total_value' in portfolio_summary:
            confidence_score += 0.2
        
        if prompt_payload.get('estimated_tokens', 0) > 1000:
            confidence_score += 0.1
        
        confidence_score = min(confidence_score, 1.0)
        
        return {
            "confidence_score": round(confidence_score, 2),
            "data_completeness": "high" if confidence_score > 0.8 else "medium" if confidence_score > 0.5 else "low",
            "strategic_readiness": "ready" if confidence_score > 0.6 else "limited_data"
        }
    
    def _assess_prompt_quality(self, prompt_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the quality of the constructed prompt."""
        prompt_text = prompt_payload.get('prompt_text', '')
        estimated_tokens = prompt_payload.get('estimated_tokens', 0)
        
        # Quality metrics
        has_research = 'Market Research Report' in prompt_text
        has_portfolio = 'Current' in prompt_text and 'balance' in prompt_text
        has_thesis = 'thesis' in prompt_text.lower()
        has_constraints = 'CONSTRAINTS' in prompt_text
        
        quality_score = sum([has_research, has_portfolio, has_thesis, has_constraints]) / 4
        
        return {
            "quality_score": round(quality_score, 2),
            "estimated_tokens": estimated_tokens,
            "has_research_context": has_research,
            "has_portfolio_context": has_portfolio,
            "has_thesis_context": has_thesis,
            "has_constraints": has_constraints,
            "prompt_completeness": "complete" if quality_score == 1.0 else "partial" if quality_score > 0.5 else "incomplete"
        }
    
    def generate_reasoning(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> str:
        """
        Generate detailed reasoning about the strategic prompt construction.
        
        Args:
            inputs: Input data including research report
            outputs: Generated prompt payload
            
        Returns:
            Natural language explanation of the strategy formulation process
        """
        if outputs.get("status") == "error":
            return f"Strategic prompt construction failed: {outputs.get('error_message', 'unknown error')}. This will prevent AI trading decisions from being made."
        
        prompt_quality = outputs.get("prompt_quality_metrics", {})
        strategy_confidence = outputs.get("strategy_confidence", {})
        research_summary = outputs.get("research_summary", {})
        portfolio_summary = outputs.get("portfolio_summary", {})
        
        reasoning = f"""
        Strategic Prompt Construction Analysis:
        
        1. Data Integration: Successfully integrated market intelligence ({research_summary.get('headline_count', 0)} headlines), portfolio state ({portfolio_summary.get('position_count', 0)} positions), and performance history
        2. Prompt Quality: {prompt_quality.get('prompt_completeness', 'unknown')} prompt with {prompt_quality.get('estimated_tokens', 0):.0f} estimated tokens
        3. Context Completeness: Research context: {prompt_quality.get('has_research_context', False)}, Portfolio context: {prompt_quality.get('has_portfolio_context', False)}, Thesis continuity: {prompt_quality.get('has_thesis_context', False)}
        4. Strategic Confidence: {strategy_confidence.get('confidence_score', 0)*100:.0f}% confidence with {strategy_confidence.get('data_completeness', 'unknown')} data completeness
        5. Market Sentiment Integration: Incorporated {research_summary.get('sentiment', 'neutral')} market sentiment with {research_summary.get('confidence', 0)*100:.0f}% confidence
        6. Risk Framework: Applied standard risk constraints with portfolio size limits and cash buffer requirements
        
        The prompt is {strategy_confidence.get('strategic_readiness', 'unknown')} for AI execution and should produce high-quality trading decisions based on comprehensive market and portfolio context.
        """
        
        return reasoning.strip()