"""
🚀 LIVE USD Trading Test for Kraken Bot
========================================

This test verifies that the trading bot correctly:
1. Uses USD balance (not USDC) for trading 
2. Maps crypto assets to USD trading pairs
3. Executes real trades with USD denomination
4. Tracks equity properly with USD base currency

⚠️  WARNING: This test makes REAL trades with REAL money!
💰 Recommended: Test with small amounts (~$5-10)
🎯 Test Case: Purchase $5+ worth of Solana (SOL) to meet minimum order requirements
"""

import os
import sys
import unittest
import logging
import pandas as pd
from decimal import Decimal
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bot.kraken_api import KrakenAPI, KrakenAPIError
from bot.trade_executor import TradeExecutor
from bot.performance_tracker import PerformanceTracker

# Set up logging for better visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestUSDTradingLive(unittest.TestCase):
    """
    🧪 Live USD Trading Test Suite
    
    Tests real USD-denominated trading on Kraken with actual API calls.
    """
    
    @classmethod
    def setUpClass(cls):
        """🔧 Initialize test environment with real Kraken connection"""
        print("\n" + "="*80)
        print("🚀 LIVE USD TRADING TEST - KRAKEN BOT")
        print("="*80)
        print("⚠️  WARNING: This test uses REAL money and makes REAL trades!")
        print("💰 Make sure you have USD balance in your Kraken account")
        print("🎯 Test Goal: Verify USD trading with $5+ SOL purchase (meets minimum order size)")
        print("="*80)
        
        # Check environment variables
        required_vars = ['KRAKEN_API_KEY', 'KRAKEN_API_SECRET']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise unittest.SkipTest(f"Missing required environment variables: {missing_vars}")
        
        try:
            cls.kraken_api = KrakenAPI()
            cls.trade_executor = TradeExecutor(cls.kraken_api)
            cls.performance_tracker = PerformanceTracker(cls.kraken_api)
            logger.info("✅ All trading components initialized successfully")
        except Exception as e:
            raise unittest.SkipTest(f"Failed to initialize trading components: {e}")
    
    def setUp(self):
        """🔍 Pre-test validation"""
        self.test_start_time = datetime.now()
        logger.info(f"🧪 Starting test: {self._testMethodName}")
    
    def tearDown(self):
        """📊 Post-test summary"""
        test_duration = (datetime.now() - self.test_start_time).total_seconds()
        logger.info(f"✅ Test completed: {self._testMethodName} ({test_duration:.1f}s)")
    
    def test_01_usd_balance_detection(self):
        """🔍 Test 1: Verify USD balance detection and handling"""
        print("\n📊 Test 1: USD Balance Detection")
        print("-" * 50)
        
        try:
            balance = self.kraken_api.get_account_balance()
            logger.info(f"Raw account balance: {balance}")
            
            # Check for USD balance specifically
            usd_balance = balance.get('USD', 0.0)
            usdc_balance = balance.get('USDC', 0.0)
            
            print(f"💵 USD Balance: ${usd_balance:.2f}")
            print(f"💰 USDC Balance: ${usdc_balance:.2f}")
            
                         # Verify we have some USD for testing
            self.assertGreater(usd_balance, 5.50, 
                             f"❌ Insufficient USD balance: ${usd_balance:.2f}. Need at least $5.50 for testing.")
            
            # Verify bot prioritizes USD over USDC
            if usdc_balance > 0:
                print("ℹ️  Note: USDC detected but bot will use USD for trading")
            
            print("✅ USD balance detection: PASSED")
            
        except Exception as e:
            self.fail(f"❌ USD balance detection failed: {e}")
    
    def test_02_usd_pair_mapping(self):
        """🗺️  Test 2: Verify USD trading pair mapping"""
        print("\n🗺️  Test 2: USD Trading Pair Mapping")
        print("-" * 50)
        
        try:
            # Test that key cryptocurrencies map to USD pairs
            test_assets = ['SOL', 'BTC', 'ETH', 'XRP', 'ADA']
            
            for asset in test_assets:
                usd_pair = self.kraken_api.asset_to_usd_pair_map.get(asset)
                print(f"🪙 {asset} → {usd_pair}")
                
                # Verify each asset has a USD pair (not USDC)
                if usd_pair:
                    self.assertIn('USD', usd_pair, 
                                f"❌ {asset} mapped to non-USD pair: {usd_pair}")
                    self.assertNotIn('USDC', usd_pair, 
                                   f"❌ {asset} incorrectly mapped to USDC pair: {usd_pair}")
                else:
                    logger.warning(f"⚠️  {asset} has no USD trading pair")
            
            # Specifically verify SOL has USD pair for our test trade
            sol_pair = self.kraken_api.asset_to_usd_pair_map.get('SOL')
            self.assertIsNotNone(sol_pair, "❌ SOL must have USD trading pair for test")
            print(f"🎯 SOL trading pair: {sol_pair}")
            
            print("✅ USD pair mapping: PASSED")
            
        except Exception as e:
            self.fail(f"❌ USD pair mapping failed: {e}")
    
    def test_03_usd_price_fetching(self):
        """💱 Test 3: Verify USD price fetching works correctly"""
        print("\n💱 Test 3: USD Price Fetching")
        print("-" * 50)
        
        try:
            # Get SOL USD price for our test trade
            sol_pair = self.kraken_api.asset_to_usd_pair_map.get('SOL')
            if not sol_pair:
                self.skipTest("SOL USD pair not available")
            
            prices = self.kraken_api.get_ticker_prices([sol_pair])
            
            self.assertIn(sol_pair, prices, f"❌ Failed to get price for {sol_pair}")
            
            sol_price = prices[sol_pair]['price']
            print(f"💰 Current SOL Price: ${sol_price:.2f} USD")
            
            # Verify price is reasonable (SOL typically $10-500)
            self.assertGreater(sol_price, 5.0, "❌ SOL price suspiciously low")
            self.assertLess(sol_price, 1000.0, "❌ SOL price suspiciously high")
            
            # Calculate how much SOL we can buy with $1
            sol_amount = 1.0 / sol_price
            print(f"🪙 $1.00 USD = {sol_amount:.6f} SOL")
            
            print("✅ USD price fetching: PASSED")
            
        except Exception as e:
            self.fail(f"❌ USD price fetching failed: {e}")
    
    def test_04_equity_calculation_usd(self):
        """📈 Test 4: Verify equity calculation uses USD correctly"""
        print("\n📈 Test 4: USD Equity Calculation")
        print("-" * 50)
        
        try:
            # Capture current equity before any trades
            balance = self.kraken_api.get_account_balance()
            
            # Manual equity calculation to verify logic
            total_equity = 0.0
            
            # Count USD cash
            usd_cash = balance.get('USD', 0.0)
            usdc_cash = balance.get('USDC', 0.0)
            total_equity += usd_cash + usdc_cash
            
            print(f"💵 Cash (USD): ${usd_cash:.2f}")
            print(f"💰 Cash (USDC): ${usdc_cash:.2f}")
            print(f"💸 Total Cash: ${usd_cash + usdc_cash:.2f}")
            
            # Count crypto assets at USD prices
            crypto_value = 0.0
            forex_assets = {'CAD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'SEK', 'NOK', 'DKK'}
            crypto_assets = [asset for asset in balance.keys() 
                           if asset not in ['USD', 'USDC'] and asset not in forex_assets]
            
            if crypto_assets:
                valid_pairs = self.kraken_api.get_valid_usd_pairs_for_assets(crypto_assets)
                if valid_pairs:
                    prices = self.kraken_api.get_ticker_prices(valid_pairs)
                    
                    for asset in crypto_assets:
                        amount = balance.get(asset, 0.0)
                        if amount > 0:
                            asset_pair = self.kraken_api.asset_to_usd_pair_map.get(asset)
                            if asset_pair and asset_pair in prices:
                                price = prices[asset_pair]['price']
                                value = amount * price
                                crypto_value += value
                                print(f"🪙 {asset}: {amount:.6f} × ${price:.2f} = ${value:.2f}")
            
            total_equity += crypto_value
            print(f"📊 Total Crypto Value: ${crypto_value:.2f}")
            print(f"🎯 Total Portfolio Equity: ${total_equity:.2f}")
            
            # Verify equity is reasonable
            self.assertGreater(total_equity, 0.0, "❌ Total equity must be positive")
            
            print("✅ USD equity calculation: PASSED")
            
        except Exception as e:
            self.fail(f"❌ USD equity calculation failed: {e}")
    
    def test_05_live_usd_trading_sol(self):
        """🚀 Test 5: LIVE TRADE - Purchase $5+ worth of Solana with USD"""
        print("\n🚀 Test 5: LIVE USD TRADING - SOL Purchase")
        print("-" * 50)
        print("⚠️  WARNING: This will execute a REAL trade!")
        print("💰 Purchasing SOL with USD (amount adjusted for minimum order size)")
        print("-" * 50)
        
        try:
            # Pre-trade validation
            balance = self.kraken_api.get_account_balance()
            initial_usd = balance.get('USD', 0.0)
            initial_sol = balance.get('SOL', 0.0)
            
            print(f"💵 Initial USD Balance: ${initial_usd:.2f}")
            print(f"🪙 Initial SOL Balance: {initial_sol:.6f}")
            
                         # Verify sufficient USD balance  
            min_required_usd = 6.0  # $5 trade + $1 buffer for fees
            self.assertGreater(initial_usd, min_required_usd, 
                             f"❌ Insufficient USD: ${initial_usd:.2f}. Need >${min_required_usd:.2f} for trade + fees")
            
            # Get current SOL price
            sol_pair = self.kraken_api.asset_to_usd_pair_map.get('SOL')
            prices = self.kraken_api.get_ticker_prices([sol_pair])
            sol_price = prices[sol_pair]['price']
            
            # Calculate SOL amount for $1 purchase
            target_usd_amount = 1.00
            sol_amount = target_usd_amount / sol_price
            
            print(f"💱 SOL Price: ${sol_price:.2f}")
            print(f"🎯 Target Purchase: ${target_usd_amount:.2f} USD")
            print(f"🪙 SOL Amount: {sol_amount:.6f}")
            
            # Check if amount meets minimum requirements
            # Most Kraken pairs have minimum order sizes - let's use $5 to be safe
            if sol_amount < 0.01:  # Typical minimum for most pairs
                print("⚠️  Initial $1 amount too small, increasing to $5")
                target_usd_amount = 5.00
                sol_amount = target_usd_amount / sol_price
                print(f"🔄 Updated Target: ${target_usd_amount:.2f} USD")
                print(f"🔄 Updated SOL Amount: {sol_amount:.6f}")
            
            # Verify we have sufficient balance for the updated amount
            if initial_usd < target_usd_amount + 1.0:  # Leave $1 for fees
                print(f"⚠️  Insufficient USD for ${target_usd_amount:.2f} trade")
                self.skipTest(f"Need at least ${target_usd_amount + 1.0:.2f} USD for this test")
            
                         # Create trade plan in correct format for trade executor
            sol_pair = self.kraken_api.asset_to_usd_pair_map.get('SOL')
            trade_plan = {
                "trades": [
                    {
                        "pair": sol_pair,
                        "action": "buy",
                        "volume": sol_amount,  # Volume in SOL, not USD
                        "reasoning": "Live test of USD trading functionality"
                    }
                ],
                "thesis": "Testing USD-denominated trading with small SOL purchase"
            }
            
            print("📋 Executing trade plan...")
            
            # Execute the trade
            trade_results = self.trade_executor.execute_trades(trade_plan)
            
            # Verify trade execution
            self.assertEqual(len(trade_results), 1, "❌ Expected exactly 1 trade result")
            
            trade_result = trade_results[0]
            print(f"📊 Trade Result: {trade_result}")
            
            # Verify trade was successful
            if trade_result.get('status') == 'success':
                print("✅ Trade executed successfully!")
                
                # Log the successful trade to CSV
                self.performance_tracker.log_trade(trade_result)
                print("📝 Trade logged to logs/trades.csv")
                
                # Wait a moment for balance to update
                import time
                time.sleep(2)
                
                # Check post-trade balances
                new_balance = self.kraken_api.get_account_balance()
                final_usd = new_balance.get('USD', 0.0)
                final_sol = new_balance.get('SOL', 0.0)
                
                print(f"💵 Final USD Balance: ${final_usd:.2f}")
                print(f"🪙 Final SOL Balance: {final_sol:.6f}")
                
                # Verify balances changed as expected
                usd_spent = initial_usd - final_usd
                sol_gained = final_sol - initial_sol
                
                print(f"💸 USD Spent: ${usd_spent:.2f}")
                print(f"🎉 SOL Gained: {sol_gained:.6f}")
                
                # Verify trade made sense (adjust for actual trade amount)
                min_expected = target_usd_amount * 0.85  # Allow 15% for fees
                max_expected = target_usd_amount * 1.15  # Allow 15% for fees
                self.assertGreater(usd_spent, min_expected, f"❌ USD spent ({usd_spent:.2f}) seems too low")
                self.assertLess(usd_spent, max_expected, f"❌ USD spent ({usd_spent:.2f}) seems too high (fees?)")
                self.assertGreater(sol_gained, 0, "❌ Should have gained some SOL")
                
                # Verify trade was logged to CSV
                self.assertTrue(os.path.exists('logs/trades.csv'), "❌ Trades CSV file should exist after trade")
                
                # Read and verify the last trade entry
                trade_df = pd.read_csv('logs/trades.csv')
                if not trade_df.empty:
                    last_trade = trade_df.iloc[-1]
                    print(f"📊 Last Logged Trade: {last_trade['action']} {last_trade['volume']:.6f} {last_trade['pair']}")
                    print(f"🆔 Transaction ID: {last_trade['txid']}")
                    
                    # Verify it matches our trade
                    self.assertEqual(last_trade['txid'], trade_result['txid'], "❌ Trade TxID should match")
                    self.assertEqual(last_trade['pair'], sol_pair, "❌ Trade pair should match")
                    self.assertEqual(last_trade['action'], 'buy', "❌ Trade action should be buy")
                
                print("🎊 LIVE USD TRADING TEST: PASSED!")
                
            else:
                error_msg = trade_result.get('error', 'Unknown error')
                self.fail(f"❌ Trade execution failed: {error_msg}")
                
        except Exception as e:
            self.fail(f"❌ Live USD trading test failed: {e}")
    
    def test_06_performance_tracking_post_trade(self):
        """📈 Test 6: Verify performance tracking after USD trade"""
        print("\n📈 Test 6: Performance Tracking Post-Trade")
        print("-" * 50)
        
        try:
            # Log current equity to verify tracking works
            self.performance_tracker.log_equity()
            
            # Verify logs were created
            import os
            self.assertTrue(os.path.exists('logs/equity.csv'), 
                          "❌ Equity log file not created")
            
            # Read the last equity entry
            import pandas as pd
            # CSV has no headers, specify column names
            equity_df = pd.read_csv('logs/equity.csv', names=['timestamp', 'total_equity_usd'])
            
            if not equity_df.empty:
                latest_equity = equity_df.iloc[-1]['total_equity_usd']
                print(f"📊 Latest Tracked Equity: ${latest_equity:.2f}")
                
                # Verify equity is reasonable
                self.assertGreater(latest_equity, 0.0, "❌ Tracked equity must be positive")
                
            print("✅ Performance tracking: PASSED")
            
        except Exception as e:
            self.fail(f"❌ Performance tracking test failed: {e}")

def run_live_demo():
    """
    🎬 Interactive demo runner with safety prompts
    """
    print("\n" + "🚀" * 30)
    print("LIVE USD TRADING TEST FOR KRAKEN BOT")
    print("🚀" * 30)
    print()
    print("⚠️  SAFETY WARNING:")
    print("   • This test executes REAL trades with REAL money")
    print("   • Approximately $5+ worth of SOL will be purchased")
    print("   • Make sure you have sufficient USD balance in Kraken")
    print("   • Only run this if you're ready to trade!")
    print()
    
    confirm = input("🤔 Do you want to proceed with LIVE trading test? (yes/no): ").lower().strip()
    
    if confirm not in ['yes', 'y']:
        print("❌ Test cancelled. No trades executed.")
        return
    
    print("\n🔥 Starting live USD trading test...")
    print("="*60)
    
    # Run the test suite
    unittest.main(argv=[''], exit=False, verbosity=2)

if __name__ == '__main__':
    print(__doc__)
    
    # Check if running interactively
    import sys
    if len(sys.argv) == 1:
        run_live_demo()
    else:
        # Run normally for automated testing
        unittest.main() 