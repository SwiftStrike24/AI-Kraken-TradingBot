import unittest
import os
import tempfile
import shutil
import json
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

from bot.research_agent import ResearchAgent, ResearchAgentError


class TestResearchAgent(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures with a temporary directory."""
        self.test_dir = tempfile.mkdtemp()
        self.research_agent = ResearchAgent(logs_dir=self.test_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test that ResearchAgent initializes correctly."""
        self.assertIsInstance(self.research_agent, ResearchAgent)
        self.assertEqual(self.research_agent.logs_dir, self.test_dir)
        self.assertTrue(os.path.exists(self.test_dir))
        self.assertIsInstance(self.research_agent.crypto_rss_feeds, list)
        self.assertIsInstance(self.research_agent.macro_rss_feeds, list)
        self.assertIsInstance(self.research_agent.crypto_keywords, list)
        self.assertIsInstance(self.research_agent.macro_keywords, list)
    
    def test_load_cache_empty(self):
        """Test loading cache when no cache file exists."""
        cache = self.research_agent._load_cache()
        self.assertIsInstance(cache, set)
        self.assertEqual(len(cache), 0)
    
    def test_load_cache_existing(self):
        """Test loading cache from existing file."""
        # Create a test cache file
        cache_data = {
            'processed_urls': ['http://example.com/1', 'http://example.com/2'],
            'last_updated': datetime.utcnow().isoformat()
        }
        cache_path = os.path.join(self.test_dir, 'research_cache.json')
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f)
        
        # Create new agent to test loading
        agent = ResearchAgent(logs_dir=self.test_dir)
        cache = agent._load_cache()
        
        self.assertIsInstance(cache, set)
        self.assertEqual(len(cache), 2)
        self.assertIn('http://example.com/1', cache)
        self.assertIn('http://example.com/2', cache)
    
    def test_save_cache(self):
        """Test saving cache to file."""
        # Add some URLs to the cache
        self.research_agent.processed_urls.add('http://example.com/1')
        self.research_agent.processed_urls.add('http://example.com/2')
        
        # Save cache
        self.research_agent._save_cache()
        
        # Verify file exists and contains correct data
        cache_path = os.path.join(self.test_dir, 'research_cache.json')
        self.assertTrue(os.path.exists(cache_path))
        
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        self.assertIn('processed_urls', cache_data)
        self.assertIn('last_updated', cache_data)
        self.assertEqual(len(cache_data['processed_urls']), 2)
        self.assertIn('http://example.com/1', cache_data['processed_urls'])
        self.assertIn('http://example.com/2', cache_data['processed_urls'])
    
    def test_is_recent_article_true(self):
        """Test recent article detection with recent date."""
        # Test with a date from 1 hour ago
        recent_date = (datetime.utcnow() - timedelta(hours=1)).strftime('%a, %d %b %Y %H:%M:%S GMT')
        self.assertTrue(self.research_agent._is_recent_article(recent_date))
    
    def test_is_recent_article_false(self):
        """Test recent article detection with old date."""
        # Test with a date from 3 days ago
        old_date = (datetime.utcnow() - timedelta(days=3)).strftime('%a, %d %b %Y %H:%M:%S GMT')
        self.assertFalse(self.research_agent._is_recent_article(old_date))
    
    def test_is_recent_article_invalid_date(self):
        """Test recent article detection with invalid date."""
        # Should return True for unparseable dates to be safe
        self.assertTrue(self.research_agent._is_recent_article("invalid date"))
    
    def test_contains_keywords_true(self):
        """Test keyword matching when keywords are present."""
        text = "Bitcoin ETF approval by SEC creates market excitement"
        keywords = ['bitcoin', 'sec', 'regulation']
        self.assertTrue(self.research_agent._contains_keywords(text, keywords))
    
    def test_contains_keywords_false(self):
        """Test keyword matching when no keywords are present."""
        text = "Local weather forecast for tomorrow"
        keywords = ['bitcoin', 'sec', 'regulation']
        self.assertFalse(self.research_agent._contains_keywords(text, keywords))
    
    def test_contains_keywords_case_insensitive(self):
        """Test that keyword matching is case insensitive."""
        text = "BITCOIN price surges after SEC announcement"
        keywords = ['bitcoin', 'sec']
        self.assertTrue(self.research_agent._contains_keywords(text, keywords))
    
    @patch('requests.get')
    def test_fetch_from_rss_success(self, mock_get):
        """Test successful RSS feed fetching."""
        # Mock RSS response
        mock_rss_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Test Crypto News</title>
                <item>
                    <title>Bitcoin reaches new all-time high</title>
                    <link>http://example.com/bitcoin-ath</link>
                    <pubDate>''' + datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT') + '''</pubDate>
                </item>
                <item>
                    <title>SEC approves Bitcoin ETF</title>
                    <link>http://example.com/sec-etf</link>
                    <pubDate>''' + datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT') + '''</pubDate>
                </item>
            </channel>
        </rss>'''
        
        mock_response = Mock()
        mock_response.content = mock_rss_content.encode('utf-8')
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Test fetch
        headlines = self.research_agent._fetch_from_rss(
            ['http://example.com/rss'], 
            ['bitcoin', 'sec'], 
            'test news'
        )
        
        self.assertIsInstance(headlines, list)
        self.assertGreater(len(headlines), 0)
        # Should contain bitcoin-related headlines
        bitcoin_headlines = [h for h in headlines if 'bitcoin' in h.lower()]
        self.assertGreater(len(bitcoin_headlines), 0)
    
    @patch('requests.get')
    def test_fetch_from_rss_request_error(self, mock_get):
        """Test RSS feed fetching with request error."""
        mock_get.side_effect = Exception("Network error")
        
        # Should handle error gracefully and return empty list
        headlines = self.research_agent._fetch_from_rss(
            ['http://example.com/rss'], 
            ['bitcoin'], 
            'test news'
        )
        
        self.assertIsInstance(headlines, list)
        self.assertEqual(len(headlines), 0)
    
    @patch('requests.get')
    def test_fetch_from_rss_malformed_xml(self, mock_get):
        """Test RSS feed fetching with malformed XML."""
        mock_response = Mock()
        mock_response.content = b"<malformed><xml"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Should handle error gracefully and return empty list
        headlines = self.research_agent._fetch_from_rss(
            ['http://example.com/rss'], 
            ['bitcoin'], 
            'test news'
        )
        
        self.assertIsInstance(headlines, list)
        self.assertEqual(len(headlines), 0)
    
    @patch.object(ResearchAgent, '_fetch_crypto_news')
    @patch.object(ResearchAgent, '_fetch_macro_news')
    @patch.object(ResearchAgent, '_fetch_market_summary')
    def test_generate_daily_report(self, mock_market_summary, mock_macro_news, mock_crypto_news):
        """Test daily report generation."""
        # Mock the fetch methods
        mock_crypto_news.return_value = [
            "- [CoinDesk] Bitcoin reaches $100k milestone",
            "- [CoinTelegraph] Ethereum upgrade goes live"
        ]
        mock_macro_news.return_value = [
            "- [Reuters] Fed holds interest rates steady"
        ]
        mock_market_summary.return_value = "Market showing bullish sentiment"
        
        # Generate report
        report = self.research_agent.generate_daily_report()
        
        # Verify report structure
        self.assertIsInstance(report, str)
        self.assertIn("Daily Market Research Report", report)
        self.assertIn("Crypto News Headlines", report)
        self.assertIn("Macro & Regulatory Updates", report)
        self.assertIn("Market Context", report)
        self.assertIn("Bitcoin reaches $100k", report)
        self.assertIn("Fed holds interest rates", report)
        self.assertIn("bullish sentiment", report)
        
        # Verify file was saved
        report_path = os.path.join(self.test_dir, "daily_research_report.md")
        self.assertTrue(os.path.exists(report_path))
        
        with open(report_path, 'r', encoding='utf-8') as f:
            saved_report = f.read()
        
        self.assertEqual(report, saved_report)
    
    @patch.object(ResearchAgent, '_fetch_crypto_news')
    @patch.object(ResearchAgent, '_fetch_macro_news')
    @patch.object(ResearchAgent, '_fetch_market_summary')
    def test_generate_daily_report_with_errors(self, mock_market_summary, mock_macro_news, mock_crypto_news):
        """Test daily report generation when some methods fail."""
        # Mock some methods to fail
        mock_crypto_news.side_effect = Exception("RSS error")
        mock_macro_news.return_value = []  # Empty results
        mock_market_summary.return_value = "Market data available"
        
        # Should still generate a report despite errors
        report = self.research_agent.generate_daily_report()
        
        self.assertIsInstance(report, str)
        self.assertIn("Daily Market Research Report", report)
        self.assertIn("temporarily unavailable", report)
        self.assertIn("Market data available", report)
    
    def test_fetch_market_summary(self):
        """Test market summary fetching (placeholder method)."""
        summary = self.research_agent._fetch_market_summary()
        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 0)


if __name__ == '__main__':
    unittest.main()