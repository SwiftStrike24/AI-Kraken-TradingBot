# Load environment variables first, before any other imports
from dotenv import load_dotenv
load_dotenv()

import schedule
import time
import logging
from datetime import datetime

# Import the multi-agent system
from agents import SupervisorAgent
from bot.kraken_api import KrakenAPI, KrakenAPIError
from bot.logger import setup_colored_logging, get_logger

# Set up logging to a file and to the console
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler("logs/scheduler_multiagent.log"),
#         logging.StreamHandler()
#     ]
# )
# logger = logging.getLogger(__name__)

# Use the new colored logger
setup_colored_logging()
logger = get_logger(__name__)


def run_multiagent_trading_cycle():
    """
    Orchestrates the multi-agent trading cycle using the Supervisor-AI.
    
    This function replaces the monolithic trading cycle with a sophisticated
    multi-agent system that provides:
    - Specialized AI agents for each cognitive task
    - Transparent reasoning and decision audit trails
    - Robust error handling and fallback mechanisms
    - Shared context to prevent agent fragmentation
    """
    logger.info("=" * 80)
    logger.info("🚀 STARTING MULTI-AGENT TRADING CYCLE 🚀")
    logger.info("=" * 80)
    logger.info(f"Cycle initiated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}")

    try:
        # Initialize the Kraken API
        logger.info("Initializing Kraken API...")
        kraken_api = KrakenAPI()
        logger.info("✅ Kraken API initialized successfully")

        # Initialize the Supervisor-AI (which manages all other agents)
        logger.info("Initializing Supervisor-AI and agent team...")
        supervisor = SupervisorAgent(kraken_api)
        logger.info("✅ Multi-agent system initialized successfully")

        # Prepare pipeline inputs
        pipeline_inputs = {
            "cycle_trigger": "scheduled_daily_run",
            "research_focus": "general_market_analysis",
            "priority_keywords": ["bitcoin", "ethereum", "solana", "xrp", "trump", "genius", "clarity", "stablecoin", "sec", "fed", "regulation", "crypto", "project crypto", "america first", "tariff", "usa", "defi", "etf", "btc etf", "sol etf", "xrp etf", "crypto etf", "blackrock", "fidelity", "vanguard", "grayscale", "inflation", "interest rates", "rate hike", "rate cut", "powell", "fomc", "cpi", "ppi", "employment", "jobs report", "recession", "gdp", "institutional", "custody", "coinbase", "microstrategy", "tesla", "adoption"],
            "strategic_focus": "alpha_generation",
            "risk_parameters": "standard",
            "execution_mode": "live_trading",
            "cycle_timestamp": datetime.now().isoformat()
        }

        logger.info("🎯 Executing multi-agent trading pipeline...")
        logger.info("Pipeline stages: CoinGecko-AI → Analyst-AI → Strategist-AI → Trader-AI → Supervisor Review → Execution")

        # Execute the complete multi-agent pipeline
        pipeline_result = supervisor.run(pipeline_inputs)

        # Process results
        if pipeline_result.get("status") == "success":
            logger.info("🎉 MULTI-AGENT TRADING CYCLE COMPLETED SUCCESSFULLY")
            
            # Extract key metrics
            execution_duration = pipeline_result.get("execution_duration_seconds", 0)
            final_state = pipeline_result.get("final_state", "unknown")
            
            # Get pipeline summary
            pipeline_summary = pipeline_result.get("pipeline_result", {}).get("pipeline_summary", {})
            agents_executed = pipeline_summary.get("agents_executed", [])
            trades_approved = pipeline_summary.get("trades_approved", False)
            
            logger.info(f"⏱️  Execution duration: {execution_duration:.1f} seconds")
            logger.info(f"🤖 Agents executed: {', '.join(agents_executed)}")
            logger.info(f"📊 Final pipeline state: {final_state}")
            logger.info(f"✅ Trades approved: {'YES' if trades_approved else 'NO'}")
            
            # Log intelligence quality
            intelligence_quality = pipeline_summary.get("market_intelligence_quality")
            decision_quality = pipeline_summary.get("ai_decision_quality")
            
            if intelligence_quality:
                logger.info(f"📰 Market intelligence quality: {intelligence_quality}")
            if decision_quality:
                logger.info(f"🧠 AI decision quality: {decision_quality:.2f}")

            # Log any warnings or errors
            warnings = pipeline_result.get("execution_context", {}).get("warnings", [])
            errors = pipeline_result.get("execution_context", {}).get("errors", [])
            
            if warnings:
                logger.warning(f"Pipeline completed with {len(warnings)} warnings:")
                for warning in warnings:
                    logger.warning(f"  - {warning}")
            if errors:
                logger.error(f"Pipeline completed with {len(errors)} errors:")
                for error in errors:
                    logger.error(f"  - {error}")
                
        else:
            logger.error("❌ MULTI-AGENT TRADING CYCLE FAILED")
            error_type = pipeline_result.get("error_type", "Unknown")
            error_message = pipeline_result.get("error_message", "No details available")
            final_state = pipeline_result.get("final_state", "unknown")
            
            logger.error(f"💥 Error type: {error_type}")
            logger.error(f"💥 Error message: {error_message}")
            logger.error(f"📊 Final state: {final_state}")
            
            # Log execution context for debugging
            execution_context = pipeline_result.get("execution_context", {})
            if execution_context.get("errors"):
                logger.error("🔍 Detailed errors:")
                for error in execution_context["errors"]:
                    logger.error(f"   - {error}")

    except KrakenAPIError as e:
        logger.error(f"💥 Kraken API error: {e}")
        logger.error("🔧 Check API credentials and network connectivity")
        
    except Exception as e:
        logger.error(f"💥 Unexpected error in multi-agent trading cycle: {e}", exc_info=True)
        logger.error("🔧 Check logs for detailed error information")
        
    finally:
        logger.info("=" * 80)
        logger.info("🏁 MULTI-AGENT TRADING CYCLE ENDED")
        logger.info("=" * 80)
        logger.info(f"Cycle completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info("")

def run_multiagent_demo():
    """
    Run a single demonstration of the multi-agent system.
    This is useful for testing and debugging without scheduling.
    """
    logger.info("🎮 Running Multi-Agent Trading Demo")
    logger.info("This is a demonstration run - not part of the scheduled cycle")
    logger.info("")
    
    run_multiagent_trading_cycle()

def handle_user_input(input_queue):
    """
    Handle user input in a separate thread (Windows compatible).
    """
    while True:
        try:
            user_input = input().strip().lower()
            input_queue.append(user_input)
        except EOFError:
            break

def main():
    """
    Main scheduler function for the multi-agent trading bot.
    """
    print("\n" + "🚀" * 35)
    print("🤖   CHATGPT-KRAKEN MULTI-AGENT TRADING BOT   🤖")
    print("🚀" * 35)
    
    logger.info("🤖 Multi-Agent Trading Bot Scheduler Starting")
    logger.info("=" * 60)
    logger.info("🏗️  Architecture: Supervisor-AI → [CoinGecko-AI, Analyst-AI, Strategist-AI, Trader-AI]")
    logger.info("⏰ Schedule: Daily at 07:00 MST")
    logger.info("🧠 Mode: Advanced Multi-Agent Cognitive System")
    logger.info("💰 Currency: USD Trading on Kraken")
    logger.info("📊 Logging: Trades → logs/trades.csv | Equity → logs/equity.csv")
    logger.info("=" * 60)
    
    # Schedule the multi-agent trading cycle
    # Run every day at 07:00 MST
    schedule.every().day.at("07:00").do(run_multiagent_trading_cycle)
    
    logger.info("⏰ Scheduled daily multi-agent trading cycle for 07:00 MST")
    logger.info("")
    logger.info("🎯 INTERACTIVE CONTROLS:")
    logger.info("   🚀 Press [ENTER] to run trading cycle NOW")
    logger.info("   📊 Press [S] then [ENTER] to show current status")
    logger.info("   📈 Press [L] then [ENTER] to show last equity")
    logger.info("   🏦 Press [P] then [ENTER] to show current portfolio")
    logger.info("   📋 Press [T] then [ENTER] to show recent trades")
    logger.info("   🔄 Press [Ctrl+C] to stop scheduler")
    logger.info("")
    logger.info("🔄 Scheduler is now running...")
    logger.info("")
    
    # Set up input handling
    import threading
    from collections import deque
    
    input_queue = deque()
    input_thread = threading.Thread(target=handle_user_input, args=(input_queue,), daemon=True)
    input_thread.start()
    
    # Keep the scheduler running with interactive controls
    try:
        while True:
            # Check for scheduled runs
            schedule.run_pending()
            
            # Process any user input
            while input_queue:
                user_input = input_queue.popleft()
                
                if user_input == "":  # Just Enter pressed
                    logger.info("")
                    logger.info("🚀 MANUAL TRIGGER: Starting trading cycle NOW!")
                    logger.info("=" * 50)
                    try:
                        run_multiagent_trading_cycle()
                        logger.info("=" * 50)
                        logger.info("✅ Manual trading cycle completed successfully!")
                    except Exception as e:
                        logger.error(f"❌ Manual trading cycle failed: {e}", exc_info=True)
                    logger.info("")
                    logger.info("🎯 Press [ENTER] to run again, [S] for status, [L] for equity, [P] for portfolio, [T] for trades, or [Ctrl+C] to stop")
                    logger.info("")
                    
                elif user_input == "s":  # Status check
                    logger.info("")
                    logger.info("📊 CURRENT STATUS:")
                    logger.info(f"   ⏰ Next scheduled run: {schedule.next_run()}")
                    logger.info(f"   🔄 Scheduler uptime: Running")
                    logger.info(f"   📁 Logs directory: logs/")
                    logger.info(f"   💰 Trading mode: Live (USD)")
                    logger.info("")
                    
                elif user_input == "l":  # Last equity check
                    logger.info("")
                    logger.info("📈 CHECKING LAST EQUITY & CURRENT PORTFOLIO...")
                    try:
                        import pandas as pd
                        import os
                        
                        # Show last logged equity
                        if os.path.exists('logs/equity.csv'):
                            # CSV has no headers: timestamp, total_equity_usd
                            equity_df = pd.read_csv('logs/equity.csv', names=['timestamp', 'total_equity_usd'])
                            if not equity_df.empty:
                                last_equity = equity_df.iloc[-1]['total_equity_usd']
                                last_time = equity_df.iloc[-1]['timestamp']
                                logger.info(f"   💵 Last logged equity: ${last_equity:.2f}")
                                logger.info(f"   📅 Last updated: {last_time}")
                            else:
                                logger.warning("   ❌ No equity data found")
                        else:
                            logger.warning("   ❌ Equity file not found")
                        
                        # Show current live portfolio
                        logger.info("")
                        logger.info("🏦 CURRENT LIVE PORTFOLIO:")
                        try:
                            kraken_api = KrakenAPI()
                            portfolio_data = kraken_api.get_comprehensive_portfolio_context()
                            
                            logger.info(f"   💰 Live total equity: ${portfolio_data['total_equity']:,.2f}")
                            logger.info(f"   💵 Cash balance: ${portfolio_data['cash_balance']:,.2f}")
                            logger.info(f"   🪙 Crypto value: ${portfolio_data['crypto_value']:,.2f}")
                            
                            if portfolio_data['usd_values']:
                                logger.info("   📊 Current holdings:")
                                for asset, data in sorted(portfolio_data['usd_values'].items(), 
                                                         key=lambda x: x[1]['value'], reverse=True):
                                    if data['value'] > 0:
                                        allocation = portfolio_data['allocation_percentages'].get(asset, 0)
                                        if asset == 'USD':
                                            logger.info(f"      • 💵 USD: ${data['value']:,.2f} ({allocation:.1f}%)")
                                        else:
                                            logger.info(f"      • 🪙 {asset}: {data['amount']:.6f} = ${data['value']:,.2f} @ ${data['price']:,.2f} ({allocation:.1f}%)")
                            else:
                                logger.info("   📝 No holdings found")
                                
                        except Exception as portfolio_error:
                            logger.error(f"   ❌ Error fetching live portfolio: {portfolio_error}")
                            
                    except Exception as e:
                        logger.error(f"   ❌ Error reading equity: {e}", exc_info=True)
                    logger.info("")
                
                elif user_input == "p":  # Portfolio status check
                    logger.info("")
                    logger.info("🏦 DETAILED PORTFOLIO STATUS...")
                    try:
                        kraken_api = KrakenAPI()
                        portfolio_data = kraken_api.get_comprehensive_portfolio_context()
                        
                        logger.info(f"   💰 Total Portfolio Value: ${portfolio_data['total_equity']:,.2f}")
                        logger.info(f"   💵 Cash (USD/USDC/USDT): ${portfolio_data['cash_balance']:,.2f}")
                        logger.info(f"   🪙 Crypto Assets Value: ${portfolio_data['crypto_value']:,.2f}")
                        logger.info(f"   🔄 Tradeable Assets: {len(portfolio_data['tradeable_assets'])}")
                        
                        if portfolio_data['usd_values']:
                            logger.info("")
                            logger.info("   📊 ASSET BREAKDOWN:")
                            total_equity = portfolio_data['total_equity']
                            
                            for asset, data in sorted(portfolio_data['usd_values'].items(), 
                                                     key=lambda x: x[1]['value'], reverse=True):
                                if data['value'] > 0.01:  # Only show assets worth more than $0.01
                                    allocation = (data['value'] / total_equity * 100) if total_equity > 0 else 0
                                    
                                    if asset == 'USD':
                                        logger.info(f"      💵 USD Cash: ${data['value']:,.2f} ({allocation:.1f}%)")
                                    else:
                                        logger.info(f"      🪙 {asset}: {data['amount']:.8f}")
                                        logger.info(f"         └─ Value: ${data['value']:,.2f} @ ${data['price']:,.2f}")
                                        logger.info(f"         └─ Allocation: {allocation:.1f}%")
                                        
                                        # Check if asset can be traded
                                        if asset in portfolio_data['tradeable_assets']:
                                            logger.info(f"         └─ ✅ Tradeable to USD")
                                        else:
                                            logger.warning(f"         └─ ❌ Not tradeable to USD")
                        else:
                            logger.info("   📝 Portfolio is empty")
                            
                        # Show allocation summary
                        if portfolio_data['total_equity'] > 0:
                            cash_pct = (portfolio_data['cash_balance'] / portfolio_data['total_equity']) * 100
                            crypto_pct = (portfolio_data['crypto_value'] / portfolio_data['total_equity']) * 100
                            logger.info("")
                            logger.info(f"   🥧 ALLOCATION: {cash_pct:.1f}% Cash | {crypto_pct:.1f}% Crypto")
                        
                    except Exception as e:
                        logger.error(f"   ❌ Error fetching portfolio: {e}", exc_info=True)
                    logger.info("")
                    
                elif user_input == "t":  # Recent trades check
                    logger.info("")
                    logger.info("📋 CHECKING RECENT TRADES...")
                    try:
                        import pandas as pd
                        import os
                        if os.path.exists('logs/trades.csv'):
                            trades_df = pd.read_csv('logs/trades.csv')
                            if not trades_df.empty:
                                logger.info(f"   📊 Total trades: {len(trades_df)}")
                                logger.info("   🔥 Last 3 trades:")
                                for _, trade in trades_df.tail(3).iterrows():
                                    logger.info(f"      • {trade['action'].upper()} {trade['volume']:.6f} {trade['pair']} (TxID: {trade['txid']})")
                            else:
                                logger.warning("   ❌ No trades found")
                        else:
                            logger.warning("   ❌ Trades file not found")
                    except Exception as e:
                        logger.error(f"   ❌ Error reading trades: {e}", exc_info=True)
                    logger.info("")
            
            time.sleep(0.5)  # Small sleep to prevent high CPU usage
            
    except KeyboardInterrupt:
        logger.info("")
        logger.info("👋 Multi-agent scheduler stopped by user")
    except Exception as e:
        logger.error(f"💥 Scheduler error: {e}", exc_info=True)
    finally:
        logger.info("🏁 Multi-agent scheduler shutdown complete")

if __name__ == "__main__":
    # Option to run a demo or start the scheduler
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        run_multiagent_demo()
    else:
        main()