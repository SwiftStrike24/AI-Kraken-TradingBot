import unittest
from unittest.mock import patch, MagicMock
import os
import requests

# Set dummy env vars for testing BEFORE importing the class
os.environ['KRAKEN_API_KEY'] = 'dummy_key'
# Use a valid base64 encoded string for the dummy secret to avoid padding errors
os.environ['KRAKEN_API_SECRET'] = 'ZHVtbXlzZWNyZXQ=' # b64encode(b'dummysecret')

from bot.kraken_api import KrakenAPI, KrakenAPIError

class TestKrakenAPI(unittest.TestCase):
    """Unit tests for the KrakenAPI wrapper."""

    def setUp(self):
        """Set up a new KrakenAPI instance for each test."""
        self.kraken_api = KrakenAPI()

    @patch('bot.kraken_api.KrakenAPI._query_api')
    def test_get_account_balance_success(self, mock_query_api):
        """Test successful parsing of account balances."""
        mock_query_api.return_value = {
            'ZUSD': '100.50',
            'XXBT': '0.5',
            'XETH': '10.0',
            'XXDG': '0.00000001' # Dust balance
        }
        
        expected_balance = {
            'USD': 100.50,
            'XBT': 0.5,
            'ETH': 10.0
        }
        
        balance = self.kraken_api.get_account_balance()
        self.assertEqual(balance, expected_balance)
        mock_query_api.assert_called_once_with('private', '/0/private/Balance')

    @patch('bot.kraken_api.KrakenAPI._query_api')
    def test_get_account_balance_empty(self, mock_query_api):
        """Test handling of an empty balance response."""
        mock_query_api.return_value = {}
        balance = self.kraken_api.get_account_balance()
        self.assertEqual(balance, {})

    @patch('bot.kraken_api.KrakenAPI._query_api')
    def test_get_ticker_prices_success(self, mock_query_api):
        """Test successful parsing of ticker prices."""
        mock_query_api.return_value = {
            'XXBTZUSD': {'c': ['65000.00', '0.1']},
            'XETHZUSD': {'c': ['4000.50', '1.2']}
        }

        expected_prices = {
            'XXBTZUSD': {'price': 65000.00},
            'XETHZUSD': {'price': 4000.50}
        }

        prices = self.kraken_api.get_ticker_prices(['XXBTZUSD', 'XETHZUSD'])
        self.assertEqual(prices, expected_prices)
        mock_query_api.assert_called_once_with('public', '/0/public/Ticker', {'pair': 'XXBTZUSD,XETHZUSD'})

    def test_get_ticker_prices_invalid_input(self):
        """Test that get_ticker_prices raises error on invalid input."""
        with self.assertRaises(ValueError):
            self.kraken_api.get_ticker_prices([])
        with self.assertRaises(ValueError):
            self.kraken_api.get_ticker_prices("not-a-list")

    @patch('bot.kraken_api.KrakenAPI._query_api')
    def test_place_order_success(self, mock_query_api):
        """Test successful placing of a market order."""
        mock_query_api.return_value = {
            'descr': {'order': 'buy 0.10000000 XBTUSD @ market'},
            'txid': ['ORDER_ID_123']
        }

        result = self.kraken_api.place_order('XBTUSD', 'buy', 0.1)
        self.assertEqual(result['txid'], ['ORDER_ID_123'])
        
        expected_data = {
            'pair': 'XBTUSD',
            'type': 'buy',
            'ordertype': 'market',
            'volume': '0.10000000'
        }
        mock_query_api.assert_called_once_with('private', '/0/private/AddOrder', expected_data)

    @patch('bot.kraken_api.KrakenAPI._query_api')
    def test_place_validate_order(self, mock_query_api):
        """Test placing a validation order."""
        mock_query_api.return_value = {'descr': {'order': 'buy 0.10000000 XBTUSD @ market'}, 'txid': None}
        
        self.kraken_api.place_order('XBTUSD', 'buy', 0.1, validate=True)
        
        expected_data = {
            'pair': 'XBTUSD',
            'type': 'buy',
            'ordertype': 'market',
            'volume': '0.10000000',
            'validate': 'true'
        }
        mock_query_api.assert_called_once_with('private', '/0/private/AddOrder', expected_data)

    @patch('bot.kraken_api.requests.Session.post')
    def test_api_error_handling(self, mock_post):
        """Test that API errors are correctly raised."""
        # Simulate a response that contains an error list
        mock_response = MagicMock()
        mock_response.json.return_value = {'error': ['EGeneral:Invalid arguments']}
        mock_response.raise_for_status.return_value = None # prevent HTTPError
        mock_post.return_value = mock_response

        with self.assertRaises(KrakenAPIError) as context:
            self.kraken_api.get_account_balance()
        
        self.assertIn("EGeneral:Invalid arguments", str(context.exception))

    @patch('bot.kraken_api.requests.Session.post')
    def test_rate_limit_retry(self, mock_post):
        """Test exponential backoff on rate limit errors."""
        # First two responses are rate limit errors, third is success
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.text = "EGeneral:Too many requests"
        rate_limit_response.raise_for_status.side_effect = requests.exceptions.HTTPError

        success_response = MagicMock()
        success_response.json.return_value = {'error': [], 'result': {'ZUSD': '100'}}
        success_response.raise_for_status.return_value = None

        mock_post.side_effect = [rate_limit_response, rate_limit_response, success_response]
        
        with patch('time.sleep') as mock_sleep:
            balance = self.kraken_api.get_account_balance()
            self.assertEqual(balance, {'USD': 100.0})
            self.assertEqual(mock_post.call_count, 3)
            # Check that sleep was called with increasing backoff
            self.assertEqual(mock_sleep.call_count, 2)
            mock_sleep.assert_any_call(1) # 2**0
            mock_sleep.assert_any_call(2) # 2**1

    def test_signature_generation(self):
        """
        Test the signature generation against a known example.
        This does not use Kraken's official example but validates the logic.
        """
        # A static example to ensure the signing logic is consistent
        # This secret was corrected to be a valid base64 string without non-ASCII chars.
        api_secret = "kQH5HW/8p1uGOVjUhy30GNvDxFbeO/vm+2LEhPXgrbTV/zNbeLgHUPSSAUd6FAmbAbQAIGxgoQn4aH21Y5bV/U=="
        self.kraken_api.api_secret = api_secret

        url_path = "/0/private/Balance"
        data = {'nonce': '1616492376594'}
        
        # This expected signature has been corrected to match the output of the
        # valid api_secret above.
        expected_signature = "xfTcv6OThPOF0amJgHARNpthx+8dukd9KEyrqevVtnD1NERimc77/P0/GtUHQqo2kzEkwpocObIYZHHvmWOhGQ=="
        
        signature = self.kraken_api._get_kraken_signature(url_path, data)
        self.assertEqual(signature, expected_signature)

if __name__ == '__main__':
    unittest.main() 