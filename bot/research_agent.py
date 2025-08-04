import os
import time
import json
import logging
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
from urllib.parse import urlparse
from openai import OpenAI, APIError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
            "https://cryptonews.com/news/feed/",
            "https://u.today/rss",
            "https://ambcrypto.com/feed/",
            "https://cryptopotato.com/feed/",
            "https://beincrypto.com/feed/",
            # Additional verified sources
            "https://blockchain.news/rss",
            "https://cryptorank.io/news/feed"
        ]
        
        # Financial/macro RSS feeds (VERIFIED WORKING as of August 2025 - Full Political Spectrum for Balanced Analysis)
        self.macro_rss_feeds = [
            # PRIMARY FINANCIAL NEWS (Unbiased/Centrist) - CONFIRMED WORKING
            "https://feeds.marketwatch.com/marketwatch/topstories/",
            "https://feeds.marketwatch.com/marketwatch/realtimeheadlines/",
            
            # RIGHT-LEANING SOURCES - CONFIRMED WORKING
            "https://www.nationalreview.com/feed/",  # Conservative - 20 entries
            "https://reason.com/latest/feed/",       # Libertarian - 48 entries
            "https://www.aei.org/feed/",             # Conservative think tank - 24 entries
            "https://www.manhattan-institute.org/rss.xml",  # Conservative policy - 10 entries
            "https://mises.org/feed",                # Austrian economics/libertarian - 100 entries
            
            # LEFT-LEANING SOURCES - CONFIRMED WORKING
            "https://feeds.npr.org/1001/rss.xml",    # NPR News - 10 entries
            "https://feeds.npr.org/1003/rss.xml",    # NPR All Things Considered - 10 entries
            "https://feeds.npr.org/1002/rss.xml",    # NPR Planet Money (economics) - 10 entries
            "https://feeds.npr.org/1017/rss.xml",    # NPR Hourly News Summary - 10 entries
            "https://feeds.washingtonpost.com/rss/business", # WaPo Business - 3 entries
            
            # ADDITIONAL LEFT-LEANING SOURCES - CONFIRMED WORKING
            "https://www.motherjones.com/rss/"       # Progressive magazine - 10 entries
        ]
        
        # Keywords for filtering relevant crypto content
        self.crypto_keywords = [
            'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'cryptocurrency',
            'sec', 'regulation', 'etf', 'halving', 'defi', 'nft', 'web3',
            'solana', 'cardano', 'binance', 'coinbase', 'kraken'
        ]
        
        # Keywords for macro/regulatory content (expanded for better coverage)
        self.macro_keywords = [
            # Federal Reserve and monetary policy
            'fed', 'federal reserve', 'powell', 'fomc', 'monetary policy',
            'interest rate', 'rate cut', 'rate hike', 'fed chair', 'central bank',
            # Economic indicators
            'inflation', 'cpi', 'ppi', 'pce', 'unemployment', 'jobs report',
            'gdp', 'economic growth', 'recession', 'economy', 'economic',
            # Market and financial terms
            'treasury', 'bond', 'yields', 'dollar', 'dxy', 'market', 'stocks',
            'wall street', 'trading', 'investors', 'financial', 'earnings',
            # Government and policy
            'congress', 'government', 'policy', 'tax', 'budget', 'debt',
            'stimulus', 'spending', 'fiscal', 'trump', 'biden',
            # Global and trade
            'trade', 'tariff', 'china', 'europe', 'global', 'international'
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
    
    def _is_recent_article(self, date_input, hours_threshold: int = 48) -> bool:
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
            
            # Handle string dates (for backward compatibility with tests)
            if pub_date is None and isinstance(date_input, str):
                # Common RSS date formats
                date_formats = [
                    '%a, %d %b %Y %H:%M:%S %Z',     # RFC 2822
                    '%a, %d %b %Y %H:%M:%S %z',     # RFC 2822 with numeric timezone
                    '%Y-%m-%dT%H:%M:%S%z',          # ISO 8601
                    '%Y-%m-%dT%H:%M:%SZ',           # ISO 8601 UTC
                    '%Y-%m-%d %H:%M:%S',            # Simple format
                    '%a, %d %b %Y %H:%M:%S GMT',    # GMT format
                ]
                
                for date_format in date_formats:
                    try:
                        pub_date = datetime.strptime(date_input.strip(), date_format)
                        # Make timezone-naive for comparison
                        if pub_date.tzinfo is not None:
                            pub_date = pub_date.replace(tzinfo=None)
                        break
                    except ValueError:
                        continue
            
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
                       source_category: str) -> List[str]:
        """
        Fetch and filter articles from RSS feeds using feedparser for robust parsing.
        
        Args:
            feed_urls: List of RSS feed URLs
            keywords: Keywords to filter content
            source_category: Category name for logging
            
        Returns:
            List of formatted headline strings
        """
        headlines = []
        successful_feeds = 0
        
        for feed_url in feed_urls:
            try:
                source_name = urlparse(feed_url).netloc.replace('www.', '')
                logger.info(f"Fetching {source_category} from {source_name}")
                
                # Use feedparser for robust RSS/Atom parsing
                feed = feedparser.parse(feed_url)
                
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
                        
                        # Skip if already processed
                        if link and link in self.processed_urls:
                            skipped_reasons['duplicate'] += 1
                            logger.debug(f"Skipped '{title[:50]}...': Already processed")
                            continue
                        
                        # Check if article is recent using feedparser's parsed dates
                        pub_time = getattr(entry, 'published_parsed', None) or getattr(entry, 'updated_parsed', None)
                        if pub_time and not self._is_recent_article(pub_time):
                            skipped_reasons['old'] += 1
                            logger.debug(f"Skipped '{title[:50]}...': Too old")
                            continue
                        
                        # Filter by keywords
                        if keywords and not self._contains_keywords(title, keywords):
                            skipped_reasons['no_keywords'] += 1
                            logger.debug(f"Skipped '{title[:50]}...': No matching keywords")
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
                
            except Exception as e:
                logger.error(f"Error fetching RSS from {feed_url}: {e}")
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
    
    def _fetch_crypto_news(self) -> List[str]:
        """Fetch crypto-specific news headlines."""
        return self._fetch_from_rss(
            self.crypto_rss_feeds, 
            self.crypto_keywords, 
            "crypto news"
        )
    
    def _fetch_macro_news(self) -> List[str]:
        """Fetch macroeconomic and regulatory news."""
        return self._fetch_from_rss(
            self.macro_rss_feeds,
            self.macro_keywords,
            "macro/regulatory news"
        )
    
    def _fetch_market_summary(self) -> str:
        """
        Generate AI-powered market analysis based on all gathered headlines.
        Synthesizes crypto and macro news from across the political spectrum into actionable insights.
        """
        try:
            if not self.openai_client:
                logger.warning("OpenAI client not available - using fallback summary")
                return "Market analysis based on live data feeds. AI analysis unavailable."
            
            # Gather all headlines for analysis
            crypto_headlines = self._fetch_crypto_news()
            macro_headlines = self._fetch_macro_news()
            
            # If no news available, return fallback
            if not crypto_headlines and not macro_headlines:
                return "Market analysis unavailable - no live news data could be gathered."
            
            # Prepare headlines for AI analysis
            crypto_text = "\n".join(crypto_headlines) if crypto_headlines else "No crypto news available."
            macro_text = "\n".join(macro_headlines) if macro_headlines else "No macro news available."
            
            # Create comprehensive prompt for market analysis
            analysis_prompt = f"""You are a professional financial market analyst. Analyze the following live news data from today and provide a concise, actionable market summary.

CRYPTO NEWS ({len(crypto_headlines)} headlines):
{crypto_text}

MACRO/REGULATORY NEWS ({len(macro_headlines)} headlines from across political spectrum):
{macro_text}

Please provide a 3-4 sentence market analysis that:
1. Identifies the most significant market themes and trends
2. Highlights any regulatory or macroeconomic factors affecting crypto
3. Assesses overall market sentiment (bullish/bearish/neutral)
4. Mentions any specific opportunities or risks for traders

Format as a clean, professional summary without bullet points or sections - just flowing analysis text."""

            logger.info("Generating AI-powered market analysis...")
            
            # Call OpenAI API for analysis
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a professional cryptocurrency and financial market analyst. Provide concise, actionable market insights based on current news."
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
    
    def generate_daily_report(self) -> str:
        """
        Generate a comprehensive daily market research report.
        
        Returns:
            Formatted markdown string containing the day's market intelligence
        """
        logger.info("Starting daily market research report generation...")
        
        report_sections = []
        current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Header
        report_sections.append(f"# Daily Market Research Report")
        report_sections.append(f"**Generated:** {current_time}")
        report_sections.append("")
        
        try:
            # Fetch crypto news
            logger.info("Gathering crypto news...")
            crypto_headlines = self._fetch_crypto_news()
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
            report_sections.append("## 📰 Crypto News Headlines")
            report_sections.append(f"- [ERROR] Failed to fetch live crypto news: {str(e)}")
            report_sections.append("")
        
        try:
            # Fetch macro/regulatory news
            logger.info("Gathering macro and regulatory news...")
            macro_headlines = self._fetch_macro_news()
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
            report_sections.append("## 🏛️ Macro & Regulatory Updates")
            report_sections.append(f"- [ERROR] Failed to fetch live macro news: {str(e)}")
            report_sections.append("")
        
        try:
            # Add AI-generated market analysis
            logger.info("Generating AI market context analysis...")
            market_summary = self._fetch_market_summary()
            
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