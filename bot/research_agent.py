import os
import time
import json
import logging
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import requests
from urllib.parse import urlparse
from openai import OpenAI, APIError
from bot.logger import get_logger

# Set up logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = get_logger(__name__)

class ResearchAgentError(Exception):
    """Custom exception for Research Agent errors."""
    pass

class ResearchAgent:
    """
    AI Research Agent that gathers real-time market intelligence from multiple sources.
    Provides structured market context to enhance the DecisionEngine's daily analysis.
    """
    
    def __init__(self, logs_dir: str = "logs"):
        """
        Initialize the Research Agent with data sources and configuration.
        
        Args:
            logs_dir: Directory where research reports will be saved
        """
        self.logs_dir = logs_dir
        self.report_path = os.path.join(logs_dir, "daily_research_report.md")
        self.cache_path = os.path.join(logs_dir, "research_cache.json")
        
        # Ensure logs directory exists
        os.makedirs(logs_dir, exist_ok=True)
        
        # Initialize OpenAI client for AI market analysis
        try:
            self.openai_client = OpenAI()
            logger.info("OpenAI client initialized for market analysis")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI client: {e}")
            self.openai_client = None
        
        # RSS feeds for crypto news (verified working sources as of August 2025)
        self.crypto_rss_feeds = [
            # Major crypto news outlets with reliable RSS feeds
            "https://cointelegraph.com/rss",
            "https://coindesk.com/arc/outboundfeeds/rss/",
            "https://cryptoslate.com/feed/",
            "https://decrypt.co/feed",
            "https://bitcoinist.com/feed/",
            "https://u.today/rss",
            "https://ambcrypto.com/feed/",
            "https://cryptopotato.com/feed/",
            "https://beincrypto.com/feed/",
            "https://blockchain.news/rss",
            "https://bravenewcoin.com/news/rss",
            "https://forkast.news/feed/",
        ]
        
        # Financial/macro RSS feeds (VERIFIED WORKING as of August 2025 - Full Political Spectrum for Balanced Analysis)
        self.macro_rss_feeds = [
            # PRIMARY FINANCIAL NEWS (Unbiased/Centrist) - CONFIRMED WORKING
            "https://feeds.marketwatch.com/marketwatch/topstories/",
            "https://feeds.marketwatch.com/marketwatch/realtimeheadlines/",
            
            # RIGHT-LEANING SOURCES - CONFIRMED WORKING
            "https://www.nationalreview.com/feed/",
            "https://reason.com/latest/feed/",
            "https://www.aei.org/feed/",
            
            # LEFT-LEANING SOURCES - CONFIRMED WORKING
            "https://feeds.npr.org/1001/rss.xml",    # NPR News
            "https://feeds.npr.org/1004/rss.xml",    # NPR Business
            "https://www.motherjones.com/feed/",       # Progressive magazine
        ]
        
        # Keywords for filtering relevant crypto content (enhanced for August 2025)
        self.crypto_keywords = [
            # Core cryptocurrencies
            'bitcoin', 'btc', 'ethereum', 'eth', 'solana', 'sol', 'xrp', 'ripple',
            'cardano', 'ada', 'sui', 'ethena', 'ena', 'dogecoin', 'doge', 'bonk', 'fartcoin',
            # General crypto terms
            'crypto', 'cryptocurrency', 'digital asset', 'blockchain', 'defi', 'nft', 'web3',
            # Regulatory and institutional
            'sec', 'cftc', 'regulation', 'regulatory', 'genius', 'clarity', 'stablecoin',
            'project crypto', 'america first', 'trump crypto',
            # ETFs and institutional
            'etf', 'btc etf', 'sol etf', 'xrp etf', 'crypto etf', 'spot etf',
            'blackrock', 'fidelity', 'vanguard', 'grayscale', 'institutional',
            # Exchanges and platforms
            'binance', 'coinbase', 'kraken', 'custody', 'microstrategy', 'tesla',
            # Market terms
            'halving', 'mining', 'staking', 'yield', 'liquidity', 'adoption'
        ]
        
        # Keywords for macro/regulatory content (enhanced for August 2025)
        self.macro_keywords = [
            # Federal Reserve and monetary policy
            'fed', 'federal reserve', 'powell', 'fomc', 'monetary policy',
            'interest rate', 'rate rates', 'rate cut', 'rate hike', 'fed chair', 'central bank',
            # Economic indicators
            'inflation', 'cpi', 'ppi', 'pce', 'unemployment', 'jobs report', 'employment',
            'gdp', 'economic growth', 'recession', 'economy', 'economic',
            # Market and financial terms
            'treasury', 'bond', 'yields', 'dollar', 'dxy', 'market', 'stocks',
            'wall street', 'trading', 'investors', 'financial', 'earnings',
            # Government and policy
            'congress', 'government', 'policy', 'tax', 'budget', 'debt',
            'stimulus', 'spending', 'fiscal', 'trump', 'biden',
            # Global and trade
            'trade', 'tariff', 'china', 'europe', 'global', 'international',
            # Crypto-specific regulatory terms (August 2025)
            'crypto', 'bitcoin', 'ethereum', 'cryptocurrency', 'digital asset',
            'sec', 'cftc', 'regulation', 'regulatory', 'genius', 'clarity',
            'stablecoin', 'project crypto', 'america first', 'usa',
            # ETF and institutional terms
            'etf', 'btc etf', 'crypto etf', 'blackrock', 'fidelity', 'vanguard',
            'grayscale', 'institutional', 'custody', 'coinbase', 'microstrategy',
            'tesla', 'adoption', 'defi'
        ]
        
        # Load cache for preventing duplicate processing
        self.processed_urls = self._load_cache()
        
        # Clear old cache entries to ensure fresh data (keep only last 24 hours)
        self._clean_old_cache_entries()
    
    def _load_cache(self) -> set:
        """Load the cache of previously processed URLs."""
        try:
            if os.path.exists(self.cache_path):
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    return set(cache_data.get('processed_urls', []))
        except Exception as e:
            logger.warning(f"Could not load research cache: {e}")
        return set()
    
    def _save_cache(self):
        """Save the cache of processed URLs."""
        try:
            cache_data = {
                'processed_urls': list(self.processed_urls),
                'last_updated': datetime.utcnow().isoformat()
            }
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save research cache: {e}")
    
    def _clean_old_cache_entries(self):
        """Remove cache entries older than 24 hours to ensure fresh data."""
        try:
            if os.path.exists(self.cache_path):
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                last_updated_str = cache_data.get('last_updated')
                if last_updated_str:
                    last_updated = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00').replace('+00:00', ''))
                    hours_old = (datetime.utcnow() - last_updated).total_seconds() / 3600
                    
                    # Clear cache if older than 5 minutes to ensure fresh data for demo/testing
                    if hours_old > 0.083:  # 5 minutes = 0.083 hours
                        logger.info(f"Clearing cache ({hours_old:.1f} hours old) to ensure fresh data")
                        self.processed_urls = set()
                        # Delete the cache file to start fresh
                        os.remove(self.cache_path)
                    else:
                        logger.debug(f"Cache is {hours_old:.1f} hours old, keeping entries")
        except Exception as e:
            logger.warning(f"Error cleaning cache: {e}")
            # On error, clear cache to be safe
            self.processed_urls = set()
    
    def _is_recent_article(self, date_input: any, hours_threshold: int = 48) -> bool:
        """
        Check if an article was published recently.
        
        Args:
            date_input: Either a time structure from feedparser or a date string
            hours_threshold: Maximum age in hours to consider "recent"
            
        Returns:
            True if article is recent, False otherwise
        """
        try:
            if not date_input:
                # If no date information, assume it's recent to be safe
                return True
            
            pub_date = None
            
            # Handle feedparser time structure (tuple/struct)
            if hasattr(date_input, '__len__') and len(date_input) >= 6 and not isinstance(date_input, str):
                try:
                    pub_date = datetime(*date_input[:6])
                except (TypeError, ValueError):
                    pass
            
            # Handle string dates
            if pub_date is None and isinstance(date_input, str):
                from dateutil import parser
                try:
                    # Use dateutil.parser for robust, flexible date parsing
                    pub_date = parser.parse(date_input)
                    # Make timezone-naive for comparison
                    if pub_date.tzinfo is not None:
                        pub_date = pub_date.astimezone(None).replace(tzinfo=None)
                except (ValueError, TypeError):
                    logger.debug(f"Could not parse date with dateutil, defaulting to recent: {date_input}")
                    return True
            
            if pub_date is None:
                logger.debug(f"Could not parse date, defaulting to recent: {date_input}")
                return True
                
            # Check if article is within the threshold
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_threshold)
            is_recent = pub_date >= cutoff_time
            
            hours_old = (datetime.utcnow() - pub_date).total_seconds() / 3600
            logger.debug(f"Article is {hours_old:.1f} hours old (threshold: {hours_threshold}h) - {'RECENT' if is_recent else 'OLD'}")
            
            return is_recent
            
        except Exception as e:
            logger.warning(f"Error checking article recency: {e}")
            return True  # Default to including articles if date check fails
    
    def _contains_keywords(self, text: str, keywords: List[str]) -> bool:
        """Check if text contains any of the specified keywords (case-insensitive)."""
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)
    
    def _fetch_from_rss(self, feed_urls: List[str], keywords: List[str], 
                       source_category: str, bypass_cache: bool = False) -> List[str]:
        """
        Fetch and filter articles from RSS feeds using feedparser for robust parsing.
        
        Args:
            feed_urls: List of RSS feed URLs
            keywords: Keywords to filter content
            source_category: Category name for logging
            bypass_cache: If True, re-processes all recent articles, ignoring the URL cache.
            
        Returns:
            List of formatted headline strings
        """
        headlines = []
        successful_feeds = 0
        
        # Use a standard browser User-Agent to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        for feed_url in feed_urls:
            try:
                source_name = urlparse(feed_url).netloc.replace('www.', '')
                logger.info(f"Fetching {source_category} from {source_name}")
                
                # Use a session object for potential connection pooling
                with requests.Session() as s:
                    s.headers.update(headers)
                    response = s.get(feed_url, timeout=15)
                    response.raise_for_status()
                
                # Use feedparser for robust RSS/Atom parsing
                feed = feedparser.parse(response.content)
                
                # Check if feed was parsed successfully
                if hasattr(feed, 'bozo') and feed.bozo:
                    logger.warning(f"Feed parsing issues for {source_name}: {getattr(feed, 'bozo_exception', 'Unknown error')}")
                
                # Check if we got any entries
                if not hasattr(feed, 'entries') or not feed.entries:
                    logger.warning(f"No entries found in feed from {source_name}")
                    continue
                
                feed_headlines = 0
                processed_in_feed = 0
                skipped_reasons = {'old': 0, 'no_keywords': 0, 'duplicate': 0, 'no_title': 0}
                
                # Process entries (limit to 15 most recent per feed)
                for entry in feed.entries[:15]:
                    processed_in_feed += 1
                    
                    try:
                        # Extract title
                        title = getattr(entry, 'title', '').strip()
                        if not title:
                            skipped_reasons['no_title'] += 1
                            logger.debug(f"Skipped entry {processed_in_feed}: No title")
                            continue
                        
                        # Extract link
                        link = getattr(entry, 'link', '').strip()
                        
                        # Skip if already processed (unless cache is bypassed)
                        if not bypass_cache and link and link in self.processed_urls:
                            skipped_reasons['duplicate'] += 1
                            logger.debug(f"Skipped (duplicate): '{title[:50]}...'")
                            continue
                        
                        # Check if article is recent using feedparser's parsed dates
                        pub_time = getattr(entry, 'published_parsed', None) or getattr(entry, 'updated_parsed', None)
                        if pub_time and not self._is_recent_article(pub_time):
                            skipped_reasons['old'] += 1
                            logger.debug(f"Skipped (too old): '{title[:50]}...'")
                            continue
                        
                        # Filter by keywords
                        if keywords and not self._contains_keywords(title, keywords):
                            skipped_reasons['no_keywords'] += 1
                            logger.debug(f"Skipped (no keywords): '{title[:50]}...'")
                            continue
                        
                        # Format headline
                        formatted_headline = f"- [{source_name.title()}] {title}"
                        if link:
                            formatted_headline += f" ([Link]({link}))"
                        
                        headlines.append(formatted_headline)
                        if link:
                            self.processed_urls.add(link)
                        feed_headlines += 1
                        
                        logger.debug(f"✅ Added: '{title[:60]}...'")
                        
                        if feed_headlines >= 3:  # Limit headlines per feed
                            break
                            
                    except Exception as e:
                        logger.warning(f"Error processing entry: {e}")
                        continue
                
                # Log detailed feed results
                if feed_headlines > 0:
                    successful_feeds += 1
                    logger.info(f"✅ {source_name}: {feed_headlines} headlines (processed {processed_in_feed} entries)")
                else:
                    logger.warning(f"❌ {source_name}: 0 headlines (skipped: {skipped_reasons})")
                
                # Rate limiting - be respectful
                time.sleep(1)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching RSS from {feed_url}: {e}")
                continue
            except Exception as e:
                logger.error(f"General error processing feed {feed_url}: {e}")
                continue
        
        logger.info(f"Successfully fetched from {successful_feeds}/{len(feed_urls)} feeds")
        logger.info(f"Collected {len(headlines)} {source_category} headlines")
        
        # Log results for transparency
        if headlines:
            logger.info(f"✅ LIVE DATA SUCCESS: Got {len(headlines)} real headlines from {source_category}")
            for i, headline in enumerate(headlines[:3]):  # Show first 3 headlines
                logger.info(f"  📰 Sample {i+1}: {headline[:100]}...")
        else:
            logger.warning(f"❌ LIVE DATA FAILURE: No {source_category} headlines collected from any RSS feed")
            logger.warning(f"   This may indicate RSS feed changes, network issues, or overly restrictive filtering")
        
        return headlines
    
    def _fetch_market_summary(self, coingecko_data: Dict[str, Any] = None, 
                              crypto_headlines: List[str] = None, 
                              macro_headlines: List[str] = None) -> str:
        """
        Generate AI-powered market analysis based on provided headlines and real-time market data.
        Synthesizes crypto news, macro news, and quantitative market data into actionable insights.
        
        Args:
            coingecko_data: Real-time market data from CoinGecko API (optional)
            crypto_headlines: Pre-fetched crypto news headlines (optional)
            macro_headlines: Pre-fetched macro news headlines (optional)
        """
        try:
            if not self.openai_client:
                logger.warning("OpenAI client not available - using fallback summary")
                return "Market analysis based on live data feeds. AI analysis unavailable."
            
            # Use provided headlines or fetch fresh ones if not provided
            if crypto_headlines is None:
                crypto_headlines = self._fetch_from_rss(self.crypto_rss_feeds, self.crypto_keywords, "crypto news")
            if macro_headlines is None:
                macro_headlines = self._fetch_from_rss(self.macro_rss_feeds, self.macro_keywords, "macro/regulatory news")
            
            # If no news available, return fallback
            if not crypto_headlines and not macro_headlines:
                return "Market analysis unavailable - no live news data could be gathered."
            
            # Prepare headlines for AI analysis
            crypto_text = "\n".join(crypto_headlines) if crypto_headlines else "No crypto news available."
            macro_text = "\n".join(macro_headlines) if macro_headlines else "No macro news available."
            
            # Prepare CoinGecko market data for analysis
            market_data_text = ""
            if coingecko_data and coingecko_data.get('market_data'):
                market_data_text = self._format_coingecko_for_ai(coingecko_data)
            else:
                market_data_text = "Real-time market data unavailable."
            
            # Create comprehensive prompt for market analysis (optimized based on OpenAI 2025 best practices)
            analysis_prompt = f"""ROLE: You are a senior cryptocurrency portfolio manager and technical analyst at a quantitative hedge fund, specializing in both fundamental and technical analysis for institutional clients.

TASK: Synthesize the following multi-source intelligence into a concise, actionable market assessment focusing on the top 10 cryptocurrency positions (BTC, ETH, SOL, ADA, XRP, SUI, ENA, DOGE, FARTCOIN, BONK).

DATA SOURCES:

QUANTITATIVE MARKET DATA:
{market_data_text}

QUALITATIVE NEWS INTELLIGENCE ({len(crypto_headlines)} crypto headlines):
{crypto_text}

MACRO/REGULATORY CONTEXT ({len(macro_headlines)} headlines):
{macro_text}

OUTPUT REQUIREMENTS:
• Target Audience: Institutional crypto traders and portfolio managers
• Format: 4-5 flowing sentences without bullet points or sections
• Update Frequency: Daily market open assessment
• Analysis Type: Combined fundamental sentiment + technical price action + quantitative metrics

SPECIFIC DELIVERABLES:
1. Quantify overall market sentiment (bullish/bearish/neutral) with confidence level
2. Identify 2-3 highest conviction trading opportunities from tracked assets
3. Highlight critical price levels and technical patterns from real-time data
4. Assess macro/regulatory risks that could impact portfolio positioning today
5. Provide clear directional bias for risk management

Deliver as professional, flowing analysis text suitable for institutional morning briefing."""

            logger.info("Generating AI-powered market analysis...")
            
            # Call OpenAI API for analysis
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a senior cryptocurrency portfolio manager and quantitative analyst at a top-tier investment firm. Your expertise spans technical analysis, fundamental research, and institutional trading strategies. You synthesize real-time market data with news sentiment to deliver precise, actionable intelligence for professional traders and portfolio managers."
                    },
                    {
                        "role": "user", 
                        "content": analysis_prompt
                    }
                ],
                max_tokens=300,
                temperature=0.1  # Low temperature for more consistent, professional analysis
            )
            
            market_analysis = response.choices[0].message.content.strip()
            
            logger.info("AI market analysis generated successfully")
            return market_analysis
            
        except APIError as e:
            logger.error(f"OpenAI API error generating market summary: {e}")
            return "Market analysis temporarily unavailable due to AI service error. Live news data successfully gathered."
        except Exception as e:
            logger.error(f"Error generating AI market summary: {e}")
            return "Market analysis based on live data feeds. AI analysis encountered an error."
    
    def _format_coingecko_for_ai(self, coingecko_data: Dict[str, Any]) -> str:
        """
        Format CoinGecko data into clean text for AI consumption.
        
        Args:
            coingecko_data: Raw CoinGecko data from the agent
            
        Returns:
            Formatted string suitable for AI prompt injection
        """
        try:
            text_parts = []
            
            # Format market data
            market_data = coingecko_data.get('market_data', {})
            if market_data:
                text_parts.append("LIVE PRICE DATA:")
                for token_id, data in market_data.items():
                    if isinstance(data, dict):
                        name = data.get('name', token_id.upper())
                        symbol = data.get('symbol', '').upper()
                        price = data.get('current_price', 'N/A')
                        change_24h = data.get('price_change_percentage_24h', 'N/A')
                        mcap_rank = data.get('market_cap_rank', 'N/A')
                        
                        # Format price change with direction indicator
                        if isinstance(change_24h, (int, float)):
                            change_str = f"{change_24h:+.2f}%" 
                            direction = "📈" if change_24h > 0 else "📉" if change_24h < 0 else "➡️"
                        else:
                            change_str = "N/A"
                            direction = "➡️"
                            
                        text_parts.append(f"• {name} ({symbol}): ${price:,.2f} {direction} {change_str} (Rank #{mcap_rank})")
            
            # Format trending data
            trending_data = coingecko_data.get('trending_data', {})
            if trending_data and trending_data.get('coins'):
                text_parts.append("\nTREDING NOW:")
                trending_coins = trending_data['coins'][:5]  # Top 5 trending
                for i, coin in enumerate(trending_coins, 1):
                    if isinstance(coin, dict):
                        item = coin.get('item', {})
                        name = item.get('name', 'Unknown')
                        symbol = item.get('symbol', 'N/A')
                        rank = item.get('market_cap_rank', 'N/A')
                        text_parts.append(f"  {i}. {name} ({symbol}) - Rank #{rank}")
            
            # Add data quality assessment
            quality = coingecko_data.get('data_quality', {})
            if quality:
                score = quality.get('quality_score', 'unknown').upper()
                text_parts.append(f"\nDATA QUALITY: {score}")
            
            return "\n".join(text_parts) if text_parts else "Market data formatting error."
            
        except Exception as e:
            logger.error(f"Error formatting CoinGecko data for AI: {e}")
            return "Market data available but formatting error occurred."
    
    def generate_daily_report(self, coingecko_data: Dict[str, Any] = None, custom_query: Optional[str] = None, bypass_cache: bool = False) -> str:
        """
        Generate a comprehensive daily market research report.
        
        Args:
            coingecko_data: Real-time market data from CoinGecko API (optional)
            custom_query: A specific, targeted query from the supervisor to override default keywords.
            bypass_cache: If True, forces re-fetching and re-processing of all recent articles.
        
        Returns:
            Formatted markdown string containing the day's market intelligence
        """
        logger.info("Starting daily market research report generation...")
        
        # --- Handle Dynamic Queries ---
        crypto_keywords = self.crypto_keywords
        macro_keywords = self.macro_keywords
        
        if custom_query:
            logger.warning(f"🎯 Overriding default research with custom query: '{custom_query}'")
            # Simple keyword extraction from the query. More advanced NLP could be used here.
            query_keywords = [word for word in custom_query.replace(",", " ").replace(":", " ").lower().split() if len(word) > 2]
            crypto_keywords = list(set(self.crypto_keywords + query_keywords))
            macro_keywords = list(set(self.macro_keywords + query_keywords))

        report_sections = []
        current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Initialize headline collections
        crypto_headlines = []
        macro_headlines = []
        
        # Header
        report_sections.append(f"# Daily Market Research Report")
        report_sections.append(f"**Generated:** {current_time}")
        report_sections.append("")
        
        try:
            # Fetch crypto news
            logger.info("Gathering crypto news...")
            crypto_headlines = self._fetch_from_rss(self.crypto_rss_feeds, crypto_keywords, "crypto news", bypass_cache=bypass_cache)
            if crypto_headlines:
                report_sections.append("## 📰 Crypto News Headlines")
                report_sections.extend(crypto_headlines)
                report_sections.append("")
                logger.info(f"Successfully gathered {len(crypto_headlines)} live crypto headlines")
            else:
                # NO MOCK DATA - Report real status
                report_sections.append("## 📰 Crypto News Headlines")
                report_sections.append("- [LIVE DATA UNAVAILABLE] No crypto headlines could be fetched from RSS feeds")
                report_sections.append("")
                logger.warning("No live crypto headlines available - RSS feeds may be down or blocked")
        
        except Exception as e:
            logger.error(f"Error fetching crypto news: {e}")
            crypto_headlines = []  # Ensure it's an empty list for market summary
            report_sections.append("## 📰 Crypto News Headlines")
            report_sections.append(f"- [ERROR] Failed to fetch live crypto news: {str(e)}")
            report_sections.append("")
        
        try:
            # Fetch macro/regulatory news
            logger.info("Gathering macro and regulatory news...")
            macro_headlines = self._fetch_from_rss(self.macro_rss_feeds, macro_keywords, "macro/regulatory news", bypass_cache=bypass_cache)
            if macro_headlines:
                report_sections.append("## 🏛️ Macro & Regulatory Updates")
                report_sections.extend(macro_headlines)
                report_sections.append("")
                logger.info(f"Successfully gathered {len(macro_headlines)} live macro/regulatory headlines")
            else:
                # NO MOCK DATA - Report real status
                report_sections.append("## 🏛️ Macro & Regulatory Updates")
                report_sections.append("- [LIVE DATA UNAVAILABLE] No macro/regulatory headlines could be fetched from RSS feeds")
                report_sections.append("")
                logger.warning("No live macro headlines available - RSS feeds may be down or blocked")
        
        except Exception as e:
            logger.error(f"Error fetching macro news: {e}")
            macro_headlines = []  # Ensure it's an empty list for market summary
            report_sections.append("## 🏛️ Macro & Regulatory Updates")
            report_sections.append(f"- [ERROR] Failed to fetch live macro news: {str(e)}")
            report_sections.append("")
        
        try:
            # Add AI-generated market analysis using already-fetched headlines
            logger.info("Generating AI market context analysis...")
            market_summary = self._fetch_market_summary(coingecko_data, crypto_headlines, macro_headlines)
            
            report_sections.append("## 📊 Market Context")
            report_sections.append("**AI-Generated Market Analysis:**")
            report_sections.append("")
            report_sections.append(market_summary)
            report_sections.append("")
            report_sections.append("*Analysis based on live news feeds from across the political spectrum*")
            report_sections.append("")
        
        except Exception as e:
            logger.error(f"Error fetching market summary: {e}")
            report_sections.append("## 📊 Market Context")
            report_sections.append(f"**[ERROR]** Market context unavailable: {str(e)}")
            report_sections.append("")
        
        # Footer
        report_sections.append("---")
        report_sections.append("*Report generated by AI Research Agent*")
        
        # Compile final report
        final_report = "\n".join(report_sections)
        
        try:
            # Save report to file
            with open(self.report_path, 'w', encoding='utf-8') as f:
                f.write(final_report)
            logger.info(f"Daily research report saved to {self.report_path}")
            
            # Save cache
            self._save_cache()
            
        except Exception as e:
            logger.error(f"Could not save research report: {e}")
        
        logger.info("Daily market research report generation completed")
        return final_report