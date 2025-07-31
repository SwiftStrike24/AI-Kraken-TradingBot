import unittest
from unittest.mock import patch, MagicMock, call

from bot.trade_executor import TradeExecutor
from bot.kraken_api import KrakenAPI, KrakenAPIError

class TestTradeExecutor(unittest.TestCase):
    """Unit tests for the TradeExecutor class."""

    def setUp(self):
        """Set up a mock KrakenAPI and a new TradeExecutor instance for each test."""
        self.mock_kraken_api = MagicMock(spec=KrakenAPI)
        self.executor = TradeExecutor(self.mock_kraken_api)

    def test_normalize_pair(self):
        """Test the pair normalization logic."""
        self.assertEqual(self.executor._normalize_pair("btc/usd"), "XBTUSD")
        self.assertEqual(self.executor._normalize_pair("ETH-USD"), "ETHUSD")
        self.assertEqual(self.executor._normalize_pair("solusd"), "SOLUSD")
        self.assertEqual(self.executor._normalize_pair("XBTUSD"), "XBTUSD")

    def test_successful_two_phase_execution(self):
        """Test a successful trade plan where validation and execution both pass."""
        trade_plan = {
            'trades': [
                {'pair': 'BTC/USD', 'action': 'buy', 'volume': 0.1},
                {'pair': 'ETH-USD', 'action': 'sell', 'volume': 2.5}
            ]
        }
        
        # Mock the API to return a successful response for both validation and execution
        self.mock_kraken_api.place_order.return_value = {'txid': ['ORDER_ID_123']}

        results = self.executor.execute_trades(trade_plan)

        # Check that place_order was called correctly for both phases
        expected_calls = [
            # Phase 1: Validation
            call(pair='XBTUSD', order_type='buy', volume=0.1, validate=True),
            call(pair='ETHUSD', order_type='sell', volume=2.5, validate=True),
            # Phase 2: Execution
            call(pair='XBTUSD', order_type='buy', volume=0.1, validate=False),
            call(pair='ETHUSD', order_type='sell', volume=2.5, validate=False)
        ]
        self.mock_kraken_api.place_order.assert_has_calls(expected_calls, any_order=False)
        self.assertEqual(self.mock_kraken_api.place_order.call_count, 4)

        # Check the final results
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['status'], 'success')
        self.assertEqual(results[1]['status'], 'success')
        self.assertEqual(results[0]['txid'], 'ORDER_ID_123')

    def test_validation_failure_aborts_execution(self):
        """Test that execution is aborted if any trade fails validation."""
        trade_plan = {
            'trades': [
                {'pair': 'BTC/USD', 'action': 'buy', 'volume': 0.1},
                {'pair': 'LTC/USD', 'action': 'buy', 'volume': 10} # This one will fail
            ]
        }
        
        # Configure mock to fail validation on the second call
        self.mock_kraken_api.place_order.side_effect = [
            {'txid': None}, # Successful validation for BTC
            KrakenAPIError("EOrder:Insufficient funds") # Failed validation for LTC
        ]

        results = self.executor.execute_trades(trade_plan)

        # Check that place_order was only called for validation and stopped after the failure
        expected_calls = [
            call(pair='XBTUSD', order_type='buy', volume=0.1, validate=True),
            call(pair='LTCUSD', order_type='buy', volume=10, validate=True),
        ]
        self.mock_kraken_api.place_order.assert_has_calls(expected_calls, any_order=False)
        self.assertEqual(self.mock_kraken_api.place_order.call_count, 2) # Not 4

        # Check the final result
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['status'], 'validation_failed')
        self.assertIn("Insufficient funds", results[0]['error'])

    def test_live_execution_failure_continues(self):
        """Test that a failure during live execution is logged but doesn't stop other trades."""
        trade_plan = {
            'trades': [
                {'pair': 'BTC/USD', 'action': 'buy', 'volume': 0.1},
                {'pair': 'ETH/USD', 'action': 'sell', 'volume': 2.0} # This one will fail live
            ]
        }

        # Configure mock to pass all validations, then fail the second live execution
        self.mock_kraken_api.place_order.side_effect = [
            # Validation phase
            {'txid': None},
            {'txid': None},
            # Execution phase
            {'txid': ['BTC_ORDER_ID']}, # Success for BTC
            KrakenAPIError("EGeneral:Internal error") # Fail for ETH
        ]

        results = self.executor.execute_trades(trade_plan)
        
        self.assertEqual(self.mock_kraken_api.place_order.call_count, 4)
        
        # Check the final results
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['status'], 'success')
        self.assertEqual(results[0]['txid'], 'BTC_ORDER_ID')
        self.assertEqual(results[1]['status'], 'execution_failed')
        self.assertIn("Internal error", results[1]['error'])

    def test_empty_trade_plan(self):
        """Test that the executor handles an empty trade plan gracefully."""
        results = self.executor.execute_trades({'trades': []})
        self.assertEqual(results, [])
        self.mock_kraken_api.place_order.assert_not_called()

    def test_invalid_trade_format(self):
        """Test that the executor handles a malformed trade object in the plan."""
        trade_plan = {'trades': [{'pair': 'BTC/USD'}]} # Missing 'action' and 'volume'
        
        results = self.executor.execute_trades(trade_plan)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['status'], 'invalid_format')
        self.assertIn("'action'", results[0]['error'])
        self.mock_kraken_api.place_order.assert_not_called()

if __name__ == '__main__':
    unittest.main() 