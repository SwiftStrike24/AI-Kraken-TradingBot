"""
Unit tests for CoinGecko Agent

Tests the functionality of the CoinGecko Agent including:
- Market data fetching
- Trending tokens retrieval
- Error handling and resilience
- Caching mechanisms
- Rate limiting
- Data quality assessment
"""

import unittest
import json
import os
import tempfile
import time
from unittest.mock import Mock, patch, mock_open
from datetime import datetime, timedelta

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.coingecko_agent import CoinGeckoAgent, CoinGeckoAPIError

class TestCoinGeckoAgent(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.agent = CoinGeckoAgent(logs_dir=self.temp_dir)
        
        # Sample market data response
        self.sample_market_data = [
            {
                'id': 'bitcoin',
                'name': 'Bitcoin',
                'symbol': 'btc',
                'current_price': 65000.0,
                'market_cap': 1280000000000,
                'market_cap_rank': 1,
                'fully_diluted_valuation': 1365000000000,
                'total_volume': 28000000000,
                'circulating_supply': 19680000,
                'total_supply': 19680000,
                'max_supply': 21000000,
                'price_change_percentage_1h_in_currency': 0.5,
                'price_change_percentage_24h_in_currency': 2.1,
                'price_change_percentage_7d_in_currency': -1.8,
                'price_change_percentage_30d_in_currency': 12.5,
                'last_updated': '2025-08-04T10:00:00.000Z'
            },
            {
                'id': 'ethereum',
                'name': 'Ethereum',
                'symbol': 'eth',
                'current_price': 3200.0,
                'market_cap': 384000000000,
                'market_cap_rank': 2,
                'fully_diluted_valuation': 384000000000,
                'total_volume': 18000000000,
                'circulating_supply': 120000000,
                'total_supply': 120000000,
                'max_supply': None,
                'price_change_percentage_1h_in_currency': -0.2,
                'price_change_percentage_24h_in_currency': 1.8,
                'price_change_percentage_7d_in_currency': 3.5,
                'price_change_percentage_30d_in_currency': 8.2,
                'last_updated': '2025-08-04T10:00:00.000Z'
            }
        ]
        
        # Sample trending data response
        self.sample_trending_data = {
            'coins': [
                {
                    'item': {
                        'id': 'solana',
                        'name': 'Solana',
                        'symbol': 'SOL',
                        'market_cap_rank': 5,
                        'thumb': 'https://coin-images.coingecko.com/coins/images/4128/thumb/solana.png',
                        'price_btc': 0.002345,
                        'score': 0
                    }
                },
                {
                    'item': {
                        'id': 'cardano',
                        'name': 'Cardano',
                        'symbol': 'ADA',
                        'market_cap_rank': 8,
                        'thumb': 'https://coin-images.coingecko.com/coins/images/975/thumb/cardano.png',
                        'price_btc': 0.000789,
                        'score': 1
                    }
                }
            ],
            'nfts': [
                {
                    'item': {
                        'id': 'cryptopunks',
                        'name': 'CryptoPunks',
                        'symbol': 'PUNK',
                        'thumb': 'https://coin-images.coingecko.com/nft_contracts/images/7/thumb/cryptopunks.png',
                        'floor_price_in_native_currency': 45.5,
                        'floor_price_24h_percentage_change': -2.1
                    }
                }
            ],
            'categories': [
                {
                    'item': {
                        'id': 1,
                        'name': 'DeFi',
                        'market_cap_1h_change': 1.2,
                        'slug': 'decentralized-finance-defi'
                    }
                }
            ]
        }
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization_success(self):
        """Test successful agent initialization."""
        self.assertEqual(self.agent.agent_name, "CoinGecko-AI")
        self.assertEqual(self.agent.base_url, "https://api.coingecko.com/api/v3")
        self.assertEqual(self.agent.min_request_interval, 2.0)
        self.assertIsInstance(self.agent.cache, dict)
    
    def test_initialization_with_api_key(self):
        """Test initialization with API key."""
        agent = CoinGeckoAgent(logs_dir=self.temp_dir, api_key="test_key")
        self.assertEqual(agent.session.headers.get('x-cg-demo-api-key'), "test_key")
    
    @patch('agents.coingecko_agent.CoinGeckoAgent._query_api')
    def test_get_token_market_data_success(self, mock_query_api):
        """Test successful token market data retrieval."""
        mock_query_api.return_value = self.sample_market_data
        
        token_ids = ['bitcoin', 'ethereum']
        result = self.agent.get_token_market_data(token_ids)
        
        # Verify API was called correctly
        mock_query_api.assert_called_once()
        call_args = mock_query_api.call_args
        self.assertEqual(call_args[0][0], '/coins/markets')
        self.assertIn('bitcoin,ethereum', call_args[0][1]['ids'])
        
        # Verify result structure
        self.assertIn('bitcoin', result)
        self.assertIn('ethereum', result)
        self.assertEqual(result['bitcoin']['name'], 'Bitcoin')
        self.assertEqual(result['bitcoin']['current_price'], 65000.0)
        self.assertEqual(result['ethereum']['name'], 'Ethereum')
        self.assertEqual(result['ethereum']['current_price'], 3200.0)
    
    @patch('agents.coingecko_agent.CoinGeckoAgent._query_api')
    def test_get_trending_tokens_success(self, mock_query_api):
        """Test successful trending tokens retrieval."""
        mock_query_api.return_value = self.sample_trending_data
        
        result = self.agent.get_trending_tokens()
        
        # Verify API was called correctly
        mock_query_api.assert_called_once_with('/search/trending', {})
        
        # Verify result structure
        self.assertIn('coins', result)
        self.assertIn('nfts', result)
        self.assertIn('categories', result)
        self.assertEqual(len(result['coins']), 2)
        self.assertEqual(result['coins'][0]['name'], 'Solana')
        self.assertEqual(result['coins'][1]['name'], 'Cardano')
        self.assertEqual(len(result['nfts']), 1)
        self.assertEqual(result['nfts'][0]['name'], 'CryptoPunks')
    
    @patch('agents.coingecko_agent.CoinGeckoAgent._query_api')
    def test_execute_success(self, mock_query_api):
        """Test successful agent execution."""
        # Mock both API calls
        mock_query_api.side_effect = [self.sample_market_data, self.sample_trending_data]
        
        inputs = {
            'token_ids': ['bitcoin', 'ethereum'],
            'include_trending': True,
            'vs_currency': 'usd'
        }
        
        result = self.agent.execute(inputs)
        
        # Verify result structure
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['agent'], 'CoinGecko-AI')
        self.assertIn('market_data', result)
        self.assertIn('trending_data', result)
        self.assertIn('data_quality', result)
        self.assertIn('cache_stats', result)
        
        # Verify data quality assessment
        quality = result['data_quality']
        self.assertEqual(quality['market_tokens_count'], 2)
        self.assertEqual(quality['trending_coins_count'], 2)
        self.assertIn(quality['quality_score'], ['excellent', 'good', 'fair', 'poor'])
    
    def test_execute_no_trending(self):
        """Test execution without trending data."""
        with patch.object(self.agent, 'get_token_market_data') as mock_market:
            mock_market.return_value = {'bitcoin': {'name': 'Bitcoin'}}
            
            inputs = {
                'token_ids': ['bitcoin'],
                'include_trending': False
            }
            
            result = self.agent.execute(inputs)
            
            self.assertEqual(result['status'], 'success')
            self.assertIn('market_data', result)
            self.assertEqual(result['trending_data'], {})
            mock_market.assert_called_once()
    
    @patch('requests.Session.get')
    def test_query_api_success(self, mock_get):
        """Test successful API query."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'test': 'data'}
        mock_get.return_value = mock_response
        
        result = self.agent._query_api('/test', {'param': 'value'})
        
        self.assertEqual(result, {'test': 'data'})
        mock_get.assert_called_once()
    
    @patch('requests.Session.get')
    def test_query_api_rate_limit_retry(self, mock_get):
        """Test API rate limit handling with retry."""
        # First call returns 429, second call succeeds
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {'Retry-After': '1'}
        
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {'test': 'data'}
        
        mock_get.side_effect = [rate_limit_response, success_response]
        
        with patch('time.sleep') as mock_sleep:
            result = self.agent._query_api('/test', {})
            
            self.assertEqual(result, {'test': 'data'})
            mock_sleep.assert_called_once_with(1)
            self.assertEqual(mock_get.call_count, 2)
    
    @patch('requests.Session.get')
    def test_query_api_timeout_error(self, mock_get):
        """Test API timeout error handling."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()
        
        with self.assertRaises(CoinGeckoAPIError) as context:
            self.agent._query_api('/test', {})
        
        self.assertIn("timed out", str(context.exception))
    
    @patch('requests.Session.get')
    def test_query_api_connection_error(self, mock_get):
        """Test API connection error handling."""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError()
        
        with self.assertRaises(CoinGeckoAPIError) as context:
            self.agent._query_api('/test', {})
        
        self.assertIn("Failed to connect", str(context.exception))
    
    @patch('requests.Session.get')
    def test_query_api_http_error(self, mock_get):
        """Test API HTTP error handling."""
        import requests
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_get.return_value = mock_response
        
        with self.assertRaises(CoinGeckoAPIError) as context:
            self.agent._query_api('/test', {})
        
        self.assertIn("Endpoint not found", str(context.exception))
    
    def test_caching_functionality(self):
        """Test caching save and load functionality."""
        # Test data caching
        test_data = {'bitcoin': {'price': 65000}}
        cache_key = 'test_key'
        
        self.agent._cache_data(cache_key, test_data)
        
        # Verify data was cached
        self.assertIn(cache_key, self.agent.cache)
        
        # Retrieve cached data
        cached_data = self.agent._get_cached_data(cache_key)
        self.assertEqual(cached_data, test_data)
    
    def test_cache_expiration(self):
        """Test cache expiration functionality."""
        test_data = {'bitcoin': {'price': 65000}}
        cache_key = 'test_key'
        
        # Manually create expired cache entry
        expired_time = (datetime.now() - timedelta(minutes=10)).isoformat()
        self.agent.cache[cache_key] = {
            'timestamp': expired_time,
            'data': test_data
        }
        
        # Try to retrieve expired data
        cached_data = self.agent._get_cached_data(cache_key)
        self.assertIsNone(cached_data)
        self.assertNotIn(cache_key, self.agent.cache)
    
    @patch('builtins.open', new_callable=mock_open, read_data='{"test_key": {"timestamp": "2025-08-04T10:00:00", "data": {"bitcoin": {"price": 65000}}}}')
    def test_load_cache_from_file(self, mock_file):
        """Test loading cache from file."""
        with patch('os.path.exists', return_value=True):
            agent = CoinGeckoAgent(logs_dir=self.temp_dir)
            
            # Verify cache was loaded (though it would be expired and cleaned)
            mock_file.assert_called()
    
    def test_assess_data_quality(self):
        """Test data quality assessment."""
        market_data = {'bitcoin': {}, 'ethereum': {}, 'solana': {}}
        trending_data = {'coins': [{}] * 8, 'nfts': [{}] * 2}
        
        quality = self.agent._assess_data_quality(market_data, trending_data)
        
        self.assertEqual(quality['market_tokens_count'], 3)
        self.assertEqual(quality['trending_coins_count'], 8)
        self.assertEqual(quality['trending_nfts_count'], 2)
        self.assertEqual(quality['quality_score'], 'fair')  # 3 tokens, 8 trending (updated thresholds)
        self.assertEqual(quality['data_freshness'], 'real-time')
    
    def test_get_cache_stats(self):
        """Test cache statistics generation."""
        # Add some cache entries
        self.agent._cache_data('key1', {'data': 'test1'})
        self.agent._cache_data('key2', {'data': 'test2'})
        
        stats = self.agent._get_cache_stats()
        
        self.assertEqual(stats['total_entries'], 2)
        self.assertEqual(stats['valid_entries'], 2)
        self.assertEqual(stats['cache_hit_ratio'], 1.0)
        self.assertEqual(stats['cache_duration_minutes'], 5.0)
    
    def test_generate_reasoning_success(self):
        """Test reasoning generation for successful execution."""
        inputs = {'token_ids': ['bitcoin']}
        outputs = {
            'status': 'success',
            'market_data': {'bitcoin': {}},
            'trending_data': {'coins': [{}] * 5},
            'data_quality': {'market_tokens_count': 1, 'trending_coins_count': 5, 'quality_score': 'good', 'data_freshness': 'real-time'},
            'cache_stats': {'cache_hit_ratio': 0.8, 'valid_entries': 4}
        }
        
        reasoning = self.agent.generate_reasoning(inputs, outputs)
        
        self.assertIn("Market Data Collection", reasoning)
        self.assertIn("1 cryptocurrencies", reasoning)
        self.assertIn("5 trending coins", reasoning)
        self.assertIn("good", reasoning)
        self.assertIn("80%", reasoning)
    
    def test_generate_reasoning_error(self):
        """Test reasoning generation for error cases."""
        inputs = {}
        outputs = {'status': 'error', 'error_message': 'API connection failed'}
        
        reasoning = self.agent.generate_reasoning(inputs, outputs)
        
        self.assertIn("Market data gathering failed", reasoning)
        self.assertIn("API connection failed", reasoning)
        self.assertIn("impact trading decision quality", reasoning)
    
    @patch('agents.coingecko_agent.CoinGeckoAgent._query_api')
    def test_rate_limiting_behavior(self, mock_query_api):
        """Test that rate limiting is enforced between requests."""
        mock_query_api.return_value = self.sample_market_data
        
        # Set up timing
        self.agent.last_request_time = time.time()
        
        with patch('time.sleep') as mock_sleep:
            # Make a request that should trigger rate limiting
            self.agent.get_token_market_data(['bitcoin'])
            
            # Verify sleep was called for rate limiting
            mock_sleep.assert_called()
    
    def test_cache_persistence(self):
        """Test that cache persists across agent instances."""
        # Cache some data
        test_data = {'bitcoin': {'price': 65000}}
        self.agent._cache_data('test_key', test_data)
        
        # Create new agent instance
        new_agent = CoinGeckoAgent(logs_dir=self.temp_dir)
        
        # Verify data is still cached
        cached_data = new_agent._get_cached_data('test_key')
        self.assertEqual(cached_data, test_data)

if __name__ == '__main__':
    unittest.main() 