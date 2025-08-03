#!/usr/bin/env python3
"""
🚀 Research Agent Live Demo Runner
=================================

This script runs a comprehensive demonstration of the Research Agent
using REAL DATA from live RSS feeds.

Features:
- Live network requests to crypto news sources
- Real keyword filtering and content processing
- Actual report generation with market intelligence
- Visual progress indicators and detailed output
- Error handling demonstration

Run this to see your Research Agent in action!
"""

import sys
import os
import time
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def print_banner():
    """Print an awesome banner."""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🚀 AI RESEARCH AGENT LIVE DEMO 🚀                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  🌐 REAL DATA DEMONSTRATION                                                  ║
║  📰 Live RSS feeds from major crypto news sources                           ║
║  🏛️  Macro and regulatory news aggregation                                   ║
║  🔍 Smart keyword filtering in action                                       ║
║  📊 Complete market intelligence reports                                    ║
║  💾 Cache management and persistence                                        ║
║  🛡️  Error handling and resilience testing                                  ║
║                                                                              ║
║  ⚠️  REQUIRES INTERNET CONNECTION                                            ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)

def check_dependencies():
    """Check if all required dependencies are available."""
    print("🔍 Checking dependencies...")
    
    try:
        import requests
        print("   ✅ requests")
    except ImportError:
        print("   ❌ requests - Please install: pip install requests")
        return False
    
    try:
        import xml.etree.ElementTree as ET
        print("   ✅ xml.etree.ElementTree")
    except ImportError:
        print("   ❌ xml.etree.ElementTree - Should be built-in")
        return False
    
    try:
        from bot.research_agent import ResearchAgent
        print("   ✅ ResearchAgent module")
    except ImportError as e:
        print(f"   ❌ ResearchAgent module - {e}")
        return False
    
    print("✅ All dependencies available!")
    return True

def check_network():
    """Check network connectivity."""
    print("\n🌐 Checking network connectivity...")
    
    try:
        import requests
        response = requests.get("https://www.google.com", timeout=5)
        if response.status_code == 200:
            print("   ✅ Internet connection active")
            return True
        else:
            print(f"   ⚠️  Unexpected response code: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Network connection failed: {e}")
        print("   🔄 Please check your internet connection and try again")
        return False

def run_quick_test():
    """Run a quick functionality test."""
    print("\n⚡ Running quick functionality test...")
    
    try:
        from bot.research_agent import ResearchAgent
        agent = ResearchAgent()
        print("   ✅ Research Agent instantiated successfully")
        
        # Test one quick method
        test_result = agent._contains_keywords("Bitcoin ETF approval", ["bitcoin", "etf"])
        if test_result:
            print("   ✅ Keyword filtering working")
        else:
            print("   ⚠️  Keyword filtering unexpected result")
        
        return True
    except Exception as e:
        print(f"   ❌ Quick test failed: {e}")
        return False

def main():
    """Main demo runner function."""
    print_banner()
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Dependency check failed. Please install missing packages.")
        return False
    
    # Check network
    if not check_network():
        print("\n❌ Network check failed. Please ensure internet connectivity.")
        return False
    
    # Quick test
    if not run_quick_test():
        print("\n❌ Quick test failed. There may be an issue with the module.")
        return False
    
    print("\n" + "="*80)
    print("🎬 STARTING LIVE DEMONSTRATION")
    print("="*80)
    print(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("📝 This demonstration will:")
    print("   1. Initialize the Research Agent")
    print("   2. Test configuration and setup") 
    print("   3. Fetch REAL crypto news from live RSS feeds")
    print("   4. Fetch REAL macro/regulatory news")
    print("   5. Generate a complete market intelligence report")
    print("   6. Test error handling and resilience")
    print("   7. Demonstrate cache functionality")
    print("\n⏱️  Expected duration: 1-3 minutes depending on network speed")
    print("🌐 Network requests will be made to major news sources")
    
    # Countdown
    print("\n🚀 Starting in:")
    for i in range(3, 0, -1):
        print(f"   {i}...")
        time.sleep(1)
    print("   GO! 🎯\n")
    
    # Import and run the live tests
    try:
        from Tests.test_research_agent_live import run_live_demo
        
        # Run the demonstration
        result = run_live_demo()
        
        print("\n" + "="*80)
        print("📊 DEMONSTRATION RESULTS")
        print("="*80)
        
        if result.wasSuccessful():
            print("🎉 ALL TESTS PASSED!")
            print("✅ Research Agent is working perfectly with real data")
            print("🚀 Ready for production deployment")
        else:
            print("⚠️  Some tests had issues:")
            if result.failures:
                print(f"   ❌ {len(result.failures)} test failures")
            if result.errors:
                print(f"   💥 {len(result.errors)} test errors")
            print("🔍 Check the detailed output above for specific issues")
        
        print(f"\n📈 Tests run: {result.testsRun}")
        print(f"⏰ End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return result.wasSuccessful()
        
    except Exception as e:
        print(f"\n💥 Demo failed to run: {e}")
        print("🔍 Please check that all files are in place and try again")
        return False

if __name__ == "__main__":
    print("🎮 Research Agent Live Demo Runner")
    print("==================================")
    
    success = main()
    
    if success:
        print("\n🎊 Demo completed successfully!")
        print("💡 Your Research Agent is ready to enhance your trading bot!")
    else:
        print("\n🔧 Demo encountered issues.")
        print("🛠️  Please review the output and fix any problems before deployment.")
    
    print("\n👋 Thanks for testing the Research Agent!")
    sys.exit(0 if success else 1)