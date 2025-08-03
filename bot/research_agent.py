import os
import time
import json
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
from urllib.parse import urlparse

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
        
        # RSS feeds for crypto news (stable, structured sources)
        self.crypto_rss_feeds = [
            "https://cointelegraph.com/rss",
            "https://coindesk.com/arc/outboundfeeds/rss/",
            "https://cryptoslate.com/feed/",
            "https://theblock.co/rss.xml",
            "https://decrypt.co/feed",
            "https://bitcoinmagazine.com/.rss/full/"
        ]
        
        # Financial/macro RSS feeds
        self.macro_rss_feeds = [
            "https://feeds.reuters.com/reuters/businessNews",
            "https://feeds.marketwatch.com/marketwatch/marketpulse/",
            "https://feeds.benzinga.com/rss/sec"
        ]
        
        # Keywords for filtering relevant crypto content
        self.crypto_keywords = [
            'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'cryptocurrency',
            'sec', 'regulation', 'etf', 'halving', 'defi', 'nft', 'web3',
            'solana', 'cardano', 'binance', 'coinbase', 'kraken'
        ]
        
        # Keywords for macro/regulatory content
        self.macro_keywords = [
            'fed', 'federal reserve', 'inflation', 'interest rate', 'cpi',
            'unemployment', 'gdp', 'treasury', 'bond', 'dollar', 'dxy'
        ]
        
        # Load cache for preventing duplicate processing
        self.processed_urls = self._load_cache()
    
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
    
    def _is_recent_article(self, pub_date_str: str, hours_threshold: int = 48) -> bool:
        """
        Check if an article was published within the specified hours threshold.
        
        Args:
            pub_date_str: Publication date string from RSS feed
            hours_threshold: Hours to look back for recent articles
            
        Returns:
            True if article is recent, False otherwise
        """
        try:
            # Common RSS date formats
            date_formats = [
                '%a, %d %b %Y %H:%M:%S %z',  # RFC 2822
                '%a, %d %b %Y %H:%M:%S %Z',  # RFC 2822 with timezone name
                '%Y-%m-%dT%H:%M:%S%z',       # ISO 8601
                '%Y-%m-%d %H:%M:%S',         # Simple format
                '%a, %d %b %Y %H:%M:%S GMT', # GMT specific
                '%a, %d %b %Y %H:%M:%S +0000' # UTC specific
            ]
            
            pub_date = None
            for date_format in date_formats:
                try:
                    pub_date = datetime.strptime(pub_date_str.strip(), date_format)
                    break
                except ValueError:
                    continue
            
            if pub_date is None:
                logger.warning(f"Could not parse date: {pub_date_str}")
                return True  # Include articles with unparseable dates to be safe
            
            # Make timezone-naive for comparison
            if pub_date.tzinfo is not None:
                pub_date = pub_date.replace(tzinfo=None)
            
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_threshold)
            return pub_date >= cutoff_time
            
        except Exception as e:
            logger.warning(f"Error checking article date: {e}")
            return True  # Include on error to be safe
    
    def _contains_keywords(self, text: str, keywords: List[str]) -> bool:
        """Check if text contains any of the specified keywords (case-insensitive)."""
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)
    
    def _fetch_from_rss(self, feed_urls: List[str], keywords: List[str], 
                       source_category: str) -> List[str]:
        """
        Fetch and filter articles from RSS feeds.
        
        Args:
            feed_urls: List of RSS feed URLs
            keywords: Keywords to filter content
            source_category: Category name for logging
            
        Returns:
            List of formatted headline strings
        """
        headlines = []
        
        for feed_url in feed_urls:
            try:
                logger.info(f"Fetching {source_category} from {urlparse(feed_url).netloc}")
                
                # Fetch RSS feed with timeout
                response = requests.get(feed_url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; TradingBot/1.0)'
                })
                response.raise_for_status()
                
                # Parse XML
                root = ET.fromstring(response.content)
                
                # Handle different RSS formats
                items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
                
                feed_headlines = 0
                for item in items[:10]:  # Limit to 10 most recent items per feed
                    try:
                        # Extract title and link
                        title_elem = item.find('title') or item.find('{http://www.w3.org/2005/Atom}title')
                        link_elem = item.find('link') or item.find('{http://www.w3.org/2005/Atom}link')
                        pub_date_elem = (item.find('pubDate') or 
                                       item.find('{http://www.w3.org/2005/Atom}published') or
                                       item.find('{http://www.w3.org/2005/Atom}updated'))
                        
                        if title_elem is None:
                            continue
                            
                        title = title_elem.text.strip() if title_elem.text else ""
                        link = ""
                        
                        if link_elem is not None:
                            # Handle different link formats
                            if link_elem.text:
                                link = link_elem.text.strip()
                            elif link_elem.get('href'):
                                link = link_elem.get('href')
                        
                        # Skip if no title or already processed
                        if not title or link in self.processed_urls:
                            continue
                        
                        # Check if article is recent
                        if pub_date_elem is not None and pub_date_elem.text:
                            if not self._is_recent_article(pub_date_elem.text):
                                continue
                        
                        # Filter by keywords
                        if keywords and not self._contains_keywords(title, keywords):
                            continue
                        
                        # Format headline
                        source_name = urlparse(feed_url).netloc.replace('www.', '').title()
                        formatted_headline = f"- [{source_name}] {title}"
                        
                        if link:
                            formatted_headline += f" ([Link]({link}))"
                        
                        headlines.append(formatted_headline)
                        self.processed_urls.add(link)
                        feed_headlines += 1
                        
                        if feed_headlines >= 3:  # Limit headlines per feed
                            break
                            
                    except Exception as e:
                        logger.warning(f"Error processing RSS item: {e}")
                        continue
                
                # Rate limiting - be respectful
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error fetching RSS from {feed_url}: {e}")
                continue
        
        logger.info(f"Collected {len(headlines)} {source_category} headlines")
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
        Fetch a quick market summary from a reliable source.
        This is a fallback method for basic market context.
        """
        try:
            # Use a simple, reliable market API for basic data
            # This is a placeholder - in production, you might use CoinGecko, CoinMarketCap, etc.
            summary = "Market data temporarily unavailable - using portfolio context only."
            logger.info("Market summary fetch completed (placeholder)")
            return summary
        except Exception as e:
            logger.warning(f"Could not fetch market summary: {e}")
            return "Market summary unavailable."
    
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
            else:
                report_sections.append("## 📰 Crypto News Headlines")
                report_sections.append("- No significant crypto news found in recent feeds")
                report_sections.append("")
        
        except Exception as e:
            logger.error(f"Error fetching crypto news: {e}")
            report_sections.append("## 📰 Crypto News Headlines")
            report_sections.append("- Crypto news temporarily unavailable")
            report_sections.append("")
        
        try:
            # Fetch macro/regulatory news
            logger.info("Gathering macro and regulatory news...")
            macro_headlines = self._fetch_macro_news()
            if macro_headlines:
                report_sections.append("## 🏛️ Macro & Regulatory Updates")
                report_sections.extend(macro_headlines)
                report_sections.append("")
            else:
                report_sections.append("## 🏛️ Macro & Regulatory Updates")
                report_sections.append("- No significant macro/regulatory updates found")
                report_sections.append("")
        
        except Exception as e:
            logger.error(f"Error fetching macro news: {e}")
            report_sections.append("## 🏛️ Macro & Regulatory Updates")
            report_sections.append("- Macro/regulatory news temporarily unavailable")
            report_sections.append("")
        
        try:
            # Add market summary
            market_summary = self._fetch_market_summary()
            report_sections.append("## 📊 Market Context")
            report_sections.append(f"- {market_summary}")
            report_sections.append("")
        
        except Exception as e:
            logger.error(f"Error fetching market summary: {e}")
            report_sections.append("## 📊 Market Context")
            report_sections.append("- Market context temporarily unavailable")
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