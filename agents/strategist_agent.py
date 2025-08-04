"""
Strategist Agent (Prompt Engineering Specialist)

This agent specializes in building sophisticated, contextual prompts for the AI trading engine.
It combines market intelligence, portfolio state, and historical performance into optimized
prompts that maximize the quality of trading decisions.

This replaces the monolithic prompt_engine.py with a more cognitive, transparent approach.
"""

import os
import logging
from typing import Dict, Any
from datetime import datetime

from .base_agent import BaseAgent
from bot.kraken_api import KrakenAPI
from bot.prompt_engine import PromptEngine, PromptEngineError

logger = logging.getLogger(__name__)

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
            research_report = inputs.get('research_report', {})
            coingecko_data = inputs.get('coingecko_data', {})
            trending_data = inputs.get('trending_data', {})
            supervisor_directives = inputs.get('supervisor_directives', {})
            
            # Gather portfolio context
            portfolio_context = self._gather_portfolio_context()
            
            # Gather historical performance context
            performance_context = self._gather_performance_context()
            
            # Gather thesis history
            thesis_context = self._gather_thesis_context()
            
            # Construct the optimized prompt using the advanced prompt engine
            prompt_payload = self._construct_prompt_payload(
                research_report, 
                coingecko_data,
                trending_data,
                portfolio_context, 
                performance_context, 
                thesis_context,
                supervisor_directives
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
    
    def _gather_portfolio_context(self) -> Dict[str, Any]:
        """
        Gather current portfolio state and balance information.
        
        Returns:
            Structured portfolio context data
        """
        try:
            # Get current balance from Kraken
            balance = self.kraken_api.get_account_balance()
            
            if not balance:
                return {
                    "status": "empty",
                    "cash_balance": 0.0,
                    "holdings": [],
                    "total_positions": 0
                }
            
            # Process cash balances
            cash_assets = {'USDC', 'USD', 'USDT'}
            total_cash = 0.0
            
            for cash_asset in cash_assets:
                if cash_asset in balance:
                    total_cash += balance.pop(cash_asset, 0.0)
            
            # Process crypto holdings
            holdings = []
            if balance:
                # Filter out forex assets
                forex_assets = {'CAD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'SEK', 'NOK', 'DKK'}
                crypto_assets = [asset for asset in balance.keys() if asset not in forex_assets]
                
                if crypto_assets:
                    valid_pairs = self.kraken_api.get_valid_usd_pairs_for_assets(crypto_assets)
                    
                    if valid_pairs:
                        prices = self.kraken_api.get_ticker_prices(valid_pairs)
                        
                        for asset, amount in balance.items():
                            if asset in crypto_assets:
                                asset_pair = self.kraken_api.asset_to_usd_pair_map.get(asset)
                                if asset_pair and asset_pair in prices:
                                    price = prices[asset_pair]['price']
                                    value = amount * price
                                    holdings.append({
                                        "asset": asset,
                                        "amount": amount,
                                        "price": price,
                                        "value": value,
                                        "pair": asset_pair
                                    })
            
            total_portfolio_value = total_cash + sum(h["value"] for h in holdings)
            
            return {
                "status": "active",
                "cash_balance": total_cash,
                "holdings": holdings,
                "total_positions": len(holdings),
                "total_portfolio_value": total_portfolio_value,
                "cash_percentage": (total_cash / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"Failed to gather portfolio context: {e}")
            return {
                "status": "error",
                "error_message": str(e),
                "cash_balance": 0.0,
                "holdings": [],
                "total_positions": 0
            }
    
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
            
            # Read the equity log
            import pandas as pd
            equity_df = pd.read_csv(self.equity_log_path)
            
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
    
    def _construct_prompt_payload(self, research_report: Dict[str, Any], coingecko_data: Dict[str, Any],
                                trending_data: Dict[str, Any], portfolio_context: Dict[str, Any], 
                                performance_context: Dict[str, Any], thesis_context: Dict[str, Any],
                                supervisor_directives: Dict[str, Any]) -> Dict[str, Any]:
        """
        Construct the final prompt payload using the advanced prompt engine.
        
        Args:
            research_report: Market intelligence from Analyst-AI
            coingecko_data: Market data from CoinGecko-AI
            trending_data: Trending tokens data from CoinGecko-AI
            portfolio_context: Current portfolio state
            performance_context: Historical performance data
            thesis_context: Previous strategic thesis
            supervisor_directives: Any special directives from the Supervisor-AI
            
        Returns:
            Complete prompt payload ready for AI execution
        """
        try:
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
                coingecko_data=coingecko_text
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
        
        text_parts = [f"Current cash balance: ${portfolio_context.get('cash_balance', 0):.2f} USD."]
        
        holdings = portfolio_context.get('holdings', [])
        if holdings:
            text_parts.append("Current Holdings:")
            for holding in holdings:
                text_parts.append(f"- {holding['asset']}: {holding['amount']:.6f} (Value: ${holding['value']:.2f} @ ${holding['price']:.2f})")
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
        total_value = portfolio_context.get('total_portfolio_value', 0)
        
        return f"${total_value:.2f} total value, {positions} positions, ${cash:.2f} cash ({portfolio_context.get('cash_percentage', 0):.1f}%)"
    
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
            "total_value": portfolio_context.get('total_portfolio_value', 0),
            "position_count": portfolio_context.get('total_positions', 0),
            "cash_percentage": portfolio_context.get('cash_percentage', 0),
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