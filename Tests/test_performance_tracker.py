import unittest
from unittest.mock import patch, MagicMock, mock_open, call
import pandas as pd

from bot.performance_tracker import PerformanceTracker
from bot.kraken_api import KrakenAPI

class TestPerformanceTracker(unittest.TestCase):
    """Unit tests for the PerformanceTracker class."""

    def setUp(self):
        """Set up a mock KrakenAPI and a new PerformanceTracker for each test."""
        self.mock_kraken_api = MagicMock(spec=KrakenAPI)
        # We can use a test-specific logs directory
        self.test_logs_dir = "tests/temp_logs" 
        self.tracker = PerformanceTracker(self.mock_kraken_api, logs_dir=self.test_logs_dir)

    @patch('bot.performance_tracker.pd.DataFrame')
    def test_log_trade_success(self, mock_df_constructor):
        """Test logging a single successful trade."""
        trade_result = {
            'status': 'success',
            'trade': {'pair': 'XBTUSD', 'action': 'buy', 'volume': 0.1},
            'txid': 'TXID12345'
        }
        self.tracker.log_trade(trade_result)

        # Assert that the DataFrame constructor was called with the correct data
        mock_df_constructor.assert_called_once()
        # Get the data that was passed to the constructor
        constructor_data = mock_df_constructor.call_args[0][0]
        self.assertEqual(constructor_data[0]['pair'], 'XBTUSD')
        self.assertEqual(constructor_data[0]['txid'], 'TXID12345')

    @patch('bot.performance_tracker.pd.DataFrame')
    def test_log_trade_failure_is_skipped(self, mock_df_constructor):
        """Test that non-successful trades are not logged."""
        trade_result = {'status': 'execution_failed', 'trade': {}, 'error': '...'}
        self.tracker.log_trade(trade_result)
        mock_df_constructor.assert_not_called()

    @patch('bot.performance_tracker.pd.DataFrame')
    def test_log_equity(self, mock_df_constructor):
        """Test the total equity calculation and logging."""
        # Mock the API responses
        self.mock_kraken_api.get_account_balance.return_value = {
            'USDC': 1000.0, 
            'XBT': 0.5,
            'ETH': 10
        }
        self.mock_kraken_api.get_ticker_prices.return_value = {
            'XXBTZUSD': {'price': 60000.0},
            'XETHZUSD': {'price': 4000.0}
        }

        self.tracker.log_equity()
        
        # Verify API calls
        self.mock_kraken_api.get_account_balance.assert_called_once()
        self.mock_kraken_api.get_ticker_prices.assert_called_once_with(['XBTUSD', 'ETHUSD'])

        # Verify the data passed to the DataFrame constructor
        # Expected: 1000 (USDC) + 0.5*60000 (XBT) + 10*4000 (ETH) = 71000
        mock_df_constructor.assert_called_once()
        constructor_data = mock_df_constructor.call_args[0][0]
        self.assertEqual(constructor_data[0]['total_equity_usd'], 71000.00)

    @patch('builtins.open', new_callable=mock_open)
    def test_log_thesis(self, mock_file):
        """Test that the thesis log is written correctly."""
        new_thesis = "Market is bullish. Long BTC."
        self.tracker.log_thesis(new_thesis)

        # Check that the file was opened in append mode
        mock_file.assert_called_with(self.tracker.thesis_log_path, 'a')
        
        # Check that the content was written
        handle = mock_file()
        handle.write.assert_any_call(new_thesis + "\n\n")
        handle.write.assert_any_call("---\n\n")

    @patch('bot.performance_tracker.os.makedirs')
    def test_logs_directory_creation(self, mock_makedirs):
        """Test that the logs directory is created if it doesn't exist."""
        PerformanceTracker(self.mock_kraken_api, logs_dir="new_logs")
        mock_makedirs.assert_called_once_with("new_logs", exist_ok=True)

if __name__ == '__main__':
    unittest.main() 