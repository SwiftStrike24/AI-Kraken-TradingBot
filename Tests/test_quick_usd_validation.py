"""
🔍 Quick USD Trading Validation (No Live Trades)
==============================================

This test validates USD trading setup WITHOUT executing real trades.
Perfect for verifying configuration before running live tests.
"""

import os
import sys
import unittest

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bot.kraken_api import KrakenAPI
from bot.trade_executor import TradeExecutor
from bot.performance_tracker import PerformanceTracker

class TestUSDTradingValidation(unittest.TestCase):
    """
    🔍 Quick USD Trading Validation - No Real Trades
    """
    
    @classmethod
    def setUpClass(cls):
        """Initialize components"""
        try:
            cls.kraken_api = KrakenAPI()
            cls.trade_executor = TradeExecutor(cls.kraken_api)
            cls.performance_tracker = PerformanceTracker(cls.kraken_api)
        except Exception as e:
            raise unittest.SkipTest(f"Failed to initialize: {e}")
    
    def test_usd_configuration(self):
        """✅ Validate USD trading configuration"""
        print("\n🔍 USD Trading Configuration Validation")
        print("-" * 50)
        
        # Check balance
        balance = self.kraken_api.get_account_balance()
        usd_balance = balance.get('USD', 0.0)
        
        print(f"💵 USD Balance: ${usd_balance:.2f}")
        
        # Check SOL mapping
        sol_pair = self.kraken_api.asset_to_usd_pair_map.get('SOL')
        print(f"🪙 SOL → {sol_pair}")
        
        self.assertIsNotNone(sol_pair, "SOL must have USD pair")
        self.assertIn('USD', sol_pair, "SOL pair must be USD-denominated")
        
        # Check price fetching
        prices = self.kraken_api.get_ticker_prices([sol_pair])
        sol_price = prices[sol_pair]['price']
        print(f"💰 SOL Price: ${sol_price:.2f}")
        
        self.assertGreater(sol_price, 0, "SOL price must be positive")
        
        print("✅ USD trading configuration: VALID")

if __name__ == '__main__':
    unittest.main() 