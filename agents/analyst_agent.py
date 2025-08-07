"""
Analyst Agent (Market Intelligence Specialist)

This agent specializes in gathering and processing real-time market intelligence
from multiple sources including news feeds, regulatory updates, and macro data.

It replaces the monolithic research_agent.py with a more focused, cognitive approach
that provides transparent reasoning about market conditions.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from .base_agent import BaseAgent
from bot.research_agent import ResearchAgent, ResearchAgentError

# logger = logging.getLogger(__name__)

class AnalystAgent(BaseAgent):
    """
    The Analyst-AI specializes in market intelligence gathering.
    
    This agent:
    1. Gathers crypto news headlines from RSS feeds
    2. Collects macro/regulatory updates
    3. Synthesizes market context and sentiment
    4. Provides structured intelligence reports to the Strategist-AI
    """
    
    def __init__(self, logs_dir: str = "logs", session_dir: str = None):
        """
        Initialize the Analyst Agent.
        
        Args:
            logs_dir: Directory for saving agent transcripts
            session_dir: Optional session directory for unified transcript storage
        """
        super().__init__("Analyst-AI", logs_dir, session_dir)
        
        # Initialize the underlying research engine
        try:
            self.research_engine = ResearchAgent(logs_dir)
            self.logger.info("Research engine initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize research engine: {e}")
            raise
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute market intelligence gathering and analysis.
        
        Args:
            inputs: Control inputs from Supervisor (contains directives and CoinGecko data)
            
        Returns:
            Structured research report with market intelligence
        """
        self.logger.info("Beginning market intelligence gathering...")
        
        # Extract any specific research directives and CoinGecko data
        research_focus = inputs.get('research_focus', 'general_market_analysis')
        priority_keywords = inputs.get('priority_keywords', [])
        coingecko_data = inputs.get('coingecko_data', None)
        bypass_cache = inputs.get('bypass_cache', False) # New flag for refinement loops
        
        try:
            # --- DYNAMIC KEYWORD OVERRIDE ---
            # If the research focus is a specific, targeted query from the supervisor,
            # use it to override the default keyword list for this run.
            is_dynamic_query = "deep dive on" in research_focus.lower() or "focus on finding" in research_focus.lower() or "propose a new plan" in research_focus.lower()
            
            if is_dynamic_query:
                self.logger.info(f"🎯 Dynamic research focus detected: {research_focus}")
                # We can extract keywords from the focus string, or use the whole string for a smart search.
                # For now, let's keep it simple and just log that we've received a dynamic query.
                # In a more advanced implementation, we could parse asset names and fetch topic-specific news.
                pass # The existing generate_daily_report will still run, but this logic can be expanded.

            # Generate the comprehensive research report with CoinGecko data
            raw_report = self.research_engine.generate_daily_report(coingecko_data, custom_query=research_focus if is_dynamic_query else None, bypass_cache=bypass_cache)
            
            # Process and structure the report
            structured_report = self._structure_report(raw_report, research_focus, priority_keywords)
            
            # Calculate volatility and trend metrics from CoinGecko data
            market_metrics = self._calculate_market_metrics(coingecko_data)
            
            self.logger.info("Market intelligence gathering completed successfully")
            
            return {
                "status": "success",
                "agent": "Analyst-AI",
                "timestamp": datetime.now().isoformat(),
                "research_report": structured_report,
                "raw_report": raw_report,
                "research_focus": research_focus,
                "priority_keywords": priority_keywords,
                "market_metrics": market_metrics,
                "intelligence_quality": self._assess_intelligence_quality(structured_report)
            }
            
        except ResearchAgentError as e:
            self.logger.error(f"Research engine error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during market analysis: {e}")
            raise
    
    def _calculate_market_metrics(self, coingecko_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate volatility and trend metrics from CoinGecko data.
        
        Args:
            coingecko_data: Real-time market data from CoinGecko-AI
            
        Returns:
            Dictionary with calculated market metrics
        """
        try:
            if not coingecko_data or 'market_data' not in coingecko_data:
                return {"status": "no_data", "metrics": {}}
            
            market_data = coingecko_data['market_data']
            metrics = {}
            
            # Parse market data for each token
            for token_info in market_data:
                if isinstance(token_info, str):
                    # Parse token string format: "**Bitcoin (BTC)** Price: $114,887.00 | Rank: #1 Changes: 1h -0.0% | 24h +0.1% | 7d -2.6%"
                    lines = token_info.split('\n')
                    for line in lines:
                        if 'Changes:' in line and '|' in line:
                            # Extract token name
                            if '**' in line:
                                token_name = line.split('**')[1].split('**')[0].split('(')[1].replace(')', '')
                            else:
                                continue
                            
                            # Extract price changes
                            changes_part = line.split('Changes:')[1].strip()
                            change_parts = changes_part.split('|')
                            
                            try:
                                # Parse percentage changes
                                h1_change = self._parse_percentage(change_parts[0])
                                h24_change = self._parse_percentage(change_parts[1])
                                d7_change = self._parse_percentage(change_parts[2])
                                
                                # Calculate metrics
                                volatility = abs(h24_change)  # Simple volatility measure
                                momentum_score = self._calculate_momentum(h1_change, h24_change, d7_change)
                                trend_direction = self._determine_trend(h1_change, h24_change, d7_change)
                                
                                metrics[token_name] = {
                                    "1h_change": h1_change,
                                    "24h_change": h24_change,
                                    "7d_change": d7_change,
                                    "volatility": volatility,
                                    "momentum_score": momentum_score,
                                    "trend_direction": trend_direction
                                }
                                
                            except Exception as e:
                                self.logger.warning(f"Error parsing metrics for {token_name}: {e}")
                                continue
            
            # Calculate overall market metrics
            if metrics:
                overall_volatility = sum(m["volatility"] for m in metrics.values()) / len(metrics)
                overall_momentum = sum(m["momentum_score"] for m in metrics.values()) / len(metrics)
                
                # Determine market regime
                market_regime = self._determine_market_regime(overall_volatility, overall_momentum)
                
                return {
                    "status": "success",
                    "individual_metrics": metrics,
                    "overall_volatility": overall_volatility,
                    "overall_momentum": overall_momentum,
                    "market_regime": market_regime,
                    "recommended_strategies": self._recommend_strategies(market_regime, overall_volatility)
                }
            
            return {"status": "insufficient_data", "metrics": {}}
            
        except Exception as e:
            self.logger.error(f"Error calculating market metrics: {e}")
            return {"status": "error", "error": str(e)}
    
    def _parse_percentage(self, text: str) -> float:
        """Parse percentage from text like '24h +0.1%' or '1h -0.0%'"""
        # Extract the percentage part
        percent_part = text.split()[-1].replace('%', '')
        return float(percent_part)
    
    def _calculate_momentum(self, h1: float, h24: float, h7d: float) -> float:
        """Calculate momentum score based on timeframe changes"""
        # Weight recent changes more heavily
        momentum = (h1 * 0.5) + (h24 * 0.3) + (h7d * 0.2)
        return momentum
    
    def _determine_trend(self, h1: float, h24: float, h7d: float) -> str:
        """Determine trend direction"""
        avg_change = (h1 + h24 + h7d) / 3
        if avg_change > 2:
            return "strong_bullish"
        elif avg_change > 0.5:
            return "bullish"
        elif avg_change > -0.5:
            return "neutral"
        elif avg_change > -2:
            return "bearish"
        else:
            return "strong_bearish"
    
    def _determine_market_regime(self, volatility: float, momentum: float) -> str:
        """Determine overall market regime"""
        if volatility > 3 and abs(momentum) > 2:
            return "high_volatility_trending"
        elif volatility > 3:
            return "high_volatility_ranging"
        elif abs(momentum) > 1:
            return "low_volatility_trending"
        else:
            return "low_volatility_ranging"
    
    def _recommend_strategies(self, regime: str, volatility: float) -> list:
        """Recommend trading strategies based on market regime"""
        if regime == "high_volatility_trending":
            return ["MOMENTUM_TRADING", "BREAKOUT_TRADING"]
        elif regime == "high_volatility_ranging":
            return ["MEAN_REVERSION", "SCALPING"]
        elif regime == "low_volatility_trending":
            return ["TREND_FOLLOWING", "ALTCOIN_ROTATION"]
        else:
            return ["DEFENSIVE_HOLDING", "ACCUMULATION"]
    
    def _structure_report(self, raw_report: str, focus: str, keywords: list) -> Dict[str, Any]:
        """
        Structure the raw research report into organized intelligence categories.
        
        Args:
            raw_report: Raw markdown report from research engine
            focus: Research focus area
            keywords: Priority keywords to highlight
            
        Returns:
            Structured intelligence report
        """
        # Parse the report sections
        sections = self._parse_report_sections(raw_report)
        
        # Analyze sentiment and key themes
        sentiment_analysis = self._analyze_market_sentiment(sections)
        key_themes = self._extract_key_themes(sections, keywords)
        
        return {
            "crypto_headlines": sections.get("crypto_news", []),
            "macro_updates": sections.get("macro_news", []),
            "market_context": sections.get("market_summary", ""),
            "sentiment_analysis": sentiment_analysis,
            "key_themes": key_themes,
            "research_focus": focus,
            "total_headlines": len(sections.get("crypto_news", [])) + len(sections.get("macro_news", [])),
            "generation_timestamp": datetime.now().isoformat()
        }
    
    def _parse_report_sections(self, raw_report: str) -> Dict[str, Any]:
        """
        Parse the markdown report into structured sections.
        
        Args:
            raw_report: Raw markdown report
            
        Returns:
            Dictionary of parsed sections
        """
        sections = {
            "crypto_news": [],
            "macro_news": [],
            "market_summary": ""
        }
        
        lines = raw_report.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            if "Crypto News Headlines" in line:
                current_section = "crypto_news"
            elif "Macro & Regulatory Updates" in line:
                current_section = "macro_news"
            elif "Market Context" in line:
                current_section = "market_summary"
            elif line.startswith("- ") and current_section in ["crypto_news", "macro_news"]:
                sections[current_section].append(line[2:])  # Remove "- " prefix
            elif current_section == "market_summary" and line and not line.startswith("#"):
                sections["market_summary"] += line + " "
        
        # Clean up market summary
        sections["market_summary"] = sections["market_summary"].strip()
        
        return sections
    
    def _analyze_market_sentiment(self, sections: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze overall market sentiment from news headlines.
        
        Args:
            sections: Parsed report sections
            
        Returns:
            Sentiment analysis results
        """
        # Simple sentiment keywords (can be enhanced with ML in the future)
        positive_keywords = [
            'surge', 'rally', 'bullish', 'gains', 'up', 'rise', 'boost', 'positive',
            'adoption', 'approval', 'breakthrough', 'milestone', 'record', 'high'
        ]
        
        negative_keywords = [
            'crash', 'dump', 'bearish', 'decline', 'fall', 'drop', 'sell-off',
            'negative', 'concern', 'risk', 'warning', 'ban', 'restriction', 'hack'
        ]
        
        all_headlines = sections.get("crypto_news", []) + sections.get("macro_news", [])
        total_headlines = len(all_headlines)
        
        if total_headlines == 0:
            return {"sentiment": "neutral", "confidence": 0.0, "reasoning": "No headlines to analyze"}
        
        positive_count = 0
        negative_count = 0
        
        for headline in all_headlines:
            headline_lower = headline.lower()
            
            for keyword in positive_keywords:
                if keyword in headline_lower:
                    positive_count += 1
                    break
            
            for keyword in negative_keywords:
                if keyword in headline_lower:
                    negative_count += 1
                    break
        
        # Calculate sentiment
        sentiment_score = (positive_count - negative_count) / total_headlines
        
        if sentiment_score > 0.1:
            sentiment = "bullish"
        elif sentiment_score < -0.1:
            sentiment = "bearish"
        else:
            sentiment = "neutral"
        
        confidence = min(abs(sentiment_score) * 2, 1.0)  # Scale to 0-1
        
        return {
            "sentiment": sentiment,
            "confidence": round(confidence, 2),
            "positive_signals": positive_count,
            "negative_signals": negative_count,
            "total_headlines": total_headlines,
            "reasoning": f"Analyzed {total_headlines} headlines: {positive_count} positive, {negative_count} negative signals"
        }
    
    def _extract_key_themes(self, sections: Dict[str, Any], priority_keywords: list) -> list:
        """
        Extract key themes and topics from the intelligence report.
        
        Args:
            sections: Parsed report sections
            priority_keywords: Keywords to prioritize
            
        Returns:
            List of key themes found in the intelligence
        """
        # Common crypto themes to track
        theme_keywords = {
            "bitcoin": ["bitcoin", "btc", "xbt"],
            "ethereum": ["ethereum", "eth", "ether"],
            "regulation": ["sec", "regulation", "regulatory", "compliance", "legal"],
            "institutional": ["institutional", "etf", "grayscale", "blackrock", "corporate"],
            "defi": ["defi", "decentralized finance", "uniswap", "compound"],
            "fed_policy": ["fed", "federal reserve", "interest rate", "monetary policy"],
            "inflation": ["inflation", "cpi", "pce", "prices"],
            "market_structure": ["market", "trading", "volume", "liquidity"]
        }
        
        # Add priority keywords as their own themes
        for keyword in priority_keywords:
            theme_keywords[keyword.lower()] = [keyword.lower()]
        
        all_text = " ".join(sections.get("crypto_news", []) + sections.get("macro_news", []) + [sections.get("market_summary", "")])
        all_text_lower = all_text.lower()
        
        detected_themes = []
        
        for theme, keywords in theme_keywords.items():
            mentions = 0
            for keyword in keywords:
                mentions += all_text_lower.count(keyword)
            
            if mentions > 0:
                detected_themes.append({
                    "theme": theme,
                    "mentions": mentions,
                    "relevance": "high" if mentions >= 3 else "medium" if mentions >= 2 else "low"
                })
        
        # Sort by number of mentions
        detected_themes.sort(key=lambda x: x["mentions"], reverse=True)
        
        return detected_themes[:10]  # Return top 10 themes
    
    def _assess_intelligence_quality(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess the quality and completeness of the gathered intelligence.
        
        Args:
            report: Structured intelligence report
            
        Returns:
            Quality assessment metrics
        """
        crypto_headlines = len(report.get("crypto_headlines", []))
        macro_headlines = len(report.get("macro_updates", []))
        total_headlines = crypto_headlines + macro_headlines
        
        # Quality scoring
        if total_headlines >= 15:
            quality_score = "excellent"
        elif total_headlines >= 10:
            quality_score = "good"
        elif total_headlines >= 5:
            quality_score = "fair"
        else:
            quality_score = "poor"
        
        return {
            "quality_score": quality_score,
            "total_headlines": total_headlines,
            "crypto_coverage": crypto_headlines,
            "macro_coverage": macro_headlines,
            "market_context_available": bool(report.get("market_context")),
            "sentiment_confidence": report.get("sentiment_analysis", {}).get("confidence", 0.0),
            "themes_detected": len(report.get("key_themes", []))
        }
    
    def generate_reasoning(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> str:
        """
        Generate detailed reasoning about the intelligence gathering process.
        
        Args:
            inputs: Input directives from supervisor
            outputs: Generated intelligence report
            
        Returns:
            Natural language explanation of the analysis process
        """
        if outputs.get("status") == "error":
            return f"Market intelligence gathering failed due to: {outputs.get('error_message', 'unknown error')}. This will impact the trading decision quality."
        
        report = outputs.get("research_report", {})
        quality = outputs.get("intelligence_quality", {})
        
        reasoning = f"""
        Market Intelligence Analysis Completed:
        
        1. Data Collection: Successfully gathered {quality.get('total_headlines', 0)} headlines from crypto and macro sources
        2. Coverage Quality: {quality.get('quality_score', 'unknown')} - {quality.get('crypto_coverage', 0)} crypto stories, {quality.get('macro_coverage', 0)} macro updates
        3. Sentiment Analysis: Market sentiment appears {report.get('sentiment_analysis', {}).get('sentiment', 'neutral')} with {report.get('sentiment_analysis', {}).get('confidence', 0.0)*100:.0f}% confidence
        4. Key Themes: Detected {len(report.get('key_themes', []))} major themes including focus on {', '.join([theme['theme'] for theme in report.get('key_themes', [])[:3]])}
        5. Strategic Impact: This intelligence provides {quality.get('quality_score', 'limited')} market context for trading decisions
        
        The research focus was '{inputs.get('research_focus', 'general')}' and the intelligence quality meets requirements for proceeding to strategy formulation.
        """
        
        return reasoning.strip()