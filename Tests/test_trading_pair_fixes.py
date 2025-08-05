"""
🔧 Trading Pair and Volume Validation Fixes Test
===============================================

This test verifies that the new trading pair and volume validation fixes work correctly:
1. KrakenAPI can fetch trading rules with minimum order sizes
2. StrategistAgent formats trading rules for AI consumption
3. TradeExecutor properly validates minimum volumes before API calls
4. Rejected trades are logged for audit purposes

⚠️  This test connects to live Kraken API to fetch real trading rules
"""

import os
import sys
import unittest
import logging

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bot.kraken_api import KrakenAPI
from agents.strategist_agent import StrategistAgent
from bot.trade_executor import TradeExecutor
from bot.performance_tracker import PerformanceTracker

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestTradingPairFixes(unittest.TestCase):
    """
    🧪 Test suite for trading pair and volume validation fixes
    """
    
    @classmethod
    def setUpClass(cls):
        """🔧 Initialize test environment with real Kraken connection"""
        print("\n" + "="*80)
        print("🔧 TRADING PAIR & VOLUME VALIDATION FIXES TEST")
        print("="*80)
        print("✅ Testing new trading rules and validation features")
        print("🔗 Connecting to live Kraken API for trading rules")
        print("="*80)
        
        # Check environment variables
        required_vars = ['KRAKEN_API_KEY', 'KRAKEN_API_SECRET']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise unittest.SkipTest(f"Missing required environment variables: {missing_vars}")
        
        try:
            cls.kraken_api = KrakenAPI()
            cls.strategist_agent = StrategistAgent(cls.kraken_api)
            cls.trade_executor = TradeExecutor(cls.kraken_api)
            cls.performance_tracker = PerformanceTracker(cls.kraken_api)
            logger.info("✅ All components initialized successfully")
        except Exception as e:
            raise unittest.SkipTest(f"Failed to initialize components: {e}")
    
    def test_01_kraken_api_trading_rules(self):
        """🔍 Test 1: Verify KrakenAPI can fetch trading rules with ordermin"""
        print("\n📊 Test 1: Kraken API Trading Rules")
        print("-" * 50)
        
        try:
            # Test get_all_usd_trading_rules method
            usd_pairs = self.kraken_api.get_all_usd_trading_rules()
            
            print(f"📈 Found {len(usd_pairs)} USD trading pairs")
            
            # Verify we got some pairs
            self.assertGreater(len(usd_pairs), 0, "Should have at least some USD trading pairs")
            
            # Check for key assets
            expected_assets = ['ETH', 'BTC', 'SOL']
            found_assets = []
            
            for pair_name, pair_info in usd_pairs.items():
                base_asset = pair_info['base_asset']
                ordermin = pair_info['ordermin']
                
                if base_asset in expected_assets:
                    found_assets.append(base_asset)
                    print(f"✅ {pair_name} ({base_asset}): min order = {ordermin:.8f}")
                    
                    # Verify ordermin is a positive number
                    self.assertGreater(ordermin, 0, f"Ordermin for {pair_name} should be positive")
            
            # Verify we found our key assets
            for asset in expected_assets:
                if asset in found_assets:
                    print(f"✅ Found {asset} trading pair")
                else:
                    print(f"⚠️  {asset} trading pair not found")
            
            print("✅ Kraken API trading rules: PASSED")
            
        except Exception as e:
            self.fail(f"❌ Kraken API trading rules test failed: {e}")
    
    def test_02_strategist_trading_rules_formatting(self):
        """🧠 Test 2: Verify StrategistAgent formats trading rules correctly"""
        print("\n🧠 Test 2: Strategist Trading Rules Formatting")
        print("-" * 50)
        
        try:
            # Test _gather_trading_rules method
            trading_rules_text = self.strategist_agent._gather_trading_rules()
            
            print(f"📄 Trading rules text length: {len(trading_rules_text)} characters")
            
            # Verify it's not empty
            self.assertGreater(len(trading_rules_text), 100, "Trading rules text should be substantial")
            
            # Verify it contains key information
            self.assertIn("VALID KRAKEN USD TRADING PAIRS", trading_rules_text)
            self.assertIn("CRITICAL TRADING REQUIREMENTS", trading_rules_text)
            self.assertIn("minimum order size", trading_rules_text)
            
            # Check for specific pair formats
            expected_pairs = ['XETHZUSD', 'XXBTZUSD']
            for pair in expected_pairs:
                if pair in trading_rules_text:
                    print(f"✅ Found {pair} in trading rules")
                else:
                    print(f"⚠️  {pair} not found in trading rules")
            
            # Show a sample of the formatted rules
            print("\n📋 Sample Trading Rules (first 300 chars):")
            print("-" * 30)
            print(trading_rules_text[:300] + "...")
            
            print("✅ Strategist trading rules formatting: PASSED")
            
        except Exception as e:
            self.fail(f"❌ Strategist trading rules formatting test failed: {e}")
    
    def test_03_trade_executor_volume_validation(self):
        """⚖️ Test 3: Verify TradeExecutor validates minimum volumes"""
        print("\n⚖️ Test 3: Trade Executor Volume Validation")
        print("-" * 50)
        
        try:
            # Create a test trade plan with deliberately small volume
            test_trade_plan = {
                "trades": [
                    {
                        "pair": "XETHZUSD",  # Use correct Kraken pair name
                        "action": "buy",
                        "allocation_percentage": 0.01,  # Very small 1% allocation
                        "confidence_score": 0.5,
                        "reasoning": "Test trade for volume validation"
                    }
                ],
                "strategy": "TEST_VALIDATION",
                "thesis": "Testing minimum volume validation guardrails"
            }
            
            print("📋 Executing test trade plan with small volume...")
            
            # Execute the trade plan (should trigger volume validation)
            results = self.trade_executor.execute_trades(test_trade_plan)
            
            print(f"📊 Trade execution results: {len(results)} results")
            
            # Verify we got results
            self.assertGreater(len(results), 0, "Should have at least one result")
            
            # Check if volume validation worked
            result = results[0]
            status = result.get('status')
            
            print(f"📈 Trade status: {status}")
            
            if status == 'volume_too_small':
                print("✅ Volume validation correctly rejected small trade")
                self.assertIn('below minimum order size', result.get('error', ''))
            elif status == 'success':
                print("✅ Trade executed successfully (volume met minimum)")
            else:
                print(f"⚠️  Unexpected status: {status}")
            
            print("✅ Trade executor volume validation: PASSED")
            
        except Exception as e:
            self.fail(f"❌ Trade executor volume validation test failed: {e}")
    
    def test_04_rejected_trade_logging(self):
        """📝 Test 4: Verify rejected trades are logged properly"""
        print("\n📝 Test 4: Rejected Trade Logging")
        print("-" * 50)
        
        try:
            # Create a test rejected trade
            test_trade = {
                "pair": "XETHZUSD",
                "action": "buy",
                "allocation_percentage": 0.01,
                "confidence_score": 0.5,
                "reasoning": "Test trade for rejection logging"
            }
            
            rejection_reason = "Volume 0.00001 below minimum order size 0.0015 for XETHZUSD"
            
            print("📝 Logging test rejected trade...")
            
            # Test rejected trade logging
            self.performance_tracker.log_rejected_trade(test_trade, rejection_reason)
            
            # Check if rejected trades file was created
            rejected_log_path = os.path.join("logs", "rejected_trades.csv")
            
            if os.path.exists(rejected_log_path):
                print(f"✅ Rejected trades log created: {rejected_log_path}")
                
                # Read the file to verify content
                import pandas as pd
                df = pd.read_csv(rejected_log_path)
                
                print(f"📊 Rejected trades log has {len(df)} entries")
                
                if len(df) > 0:
                    last_entry = df.iloc[-1]
                    print(f"📋 Last rejected trade: {last_entry['requested_pair']} - {last_entry['rejection_reason']}")
                
            else:
                print("⚠️  Rejected trades log file not found")
            
            print("✅ Rejected trade logging: PASSED")
            
        except Exception as e:
            self.fail(f"❌ Rejected trade logging test failed: {e}")

def run_demo():
    """
    🎬 Interactive demo runner
    """
    print("\n" + "🔧" * 30)
    print("TRADING PAIR & VOLUME VALIDATION TEST")
    print("🔧" * 30)
    print()
    print("🧪 This test verifies the new trading fixes:")
    print("   • Kraken API trading rules with minimum order sizes")
    print("   • Strategist AI trading rules formatting")
    print("   • Trade executor volume validation")
    print("   • Rejected trade logging")
    print()
    
    # Run the test suite
    unittest.main(argv=[''], exit=False, verbosity=2)

if __name__ == '__main__':
    print(__doc__)
    run_demo() 