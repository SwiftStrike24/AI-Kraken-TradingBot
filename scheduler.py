# Load environment variables first, before any other imports
from dotenv import load_dotenv
load_dotenv()

import schedule
import time
import logging

# Import our bot components
from bot.kraken_api import KrakenAPI, KrakenAPIError
from bot.decision_engine import DecisionEngine, DecisionEngineError
from bot.trade_executor import TradeExecutor
from bot.performance_tracker import PerformanceTracker

# Set up logging to a file and to the console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_trading_cycle():
    """
    Orchestrates the entire daily trading cycle, from getting a strategy to execution and logging.
    This function is designed to be the single entry point for a scheduled job.
    """
    logger.info("==========================================================")
    logger.info("🚀 STARTING NEW TRADING CYCLE 🚀")
    logger.info("==========================================================")

    try:
        # 1. Initialize all modules
        logger.info("Initializing bot modules...")
        kraken_api = KrakenAPI()
        decision_engine = DecisionEngine(kraken_api)
        trade_executor = TradeExecutor(kraken_api)
        tracker = PerformanceTracker(kraken_api)
        logger.info("Modules initialized successfully.")

        # 2. Get AI-powered trading strategy
        logger.info("Generating AI trading strategy...")
        trade_plan = decision_engine.generate_strategy()
        logger.info(f"AI strategy received. Thesis: {trade_plan.get('thesis')}")

        # 3. Execute trades
        logger.info("Executing trades based on the AI plan...")
        execution_results = trade_executor.execute_trades(trade_plan)
        logger.info(f"Trade execution completed. Results: {execution_results}")

        # 4. Log the results
        logger.info("Logging cycle results...")
        # Log individual successful trades
        for result in execution_results:
            if result.get('status') == 'success':
                tracker.log_trade(result)
        
        # Log the updated total equity
        tracker.log_equity()
        
        # Log the new thesis
        tracker.log_thesis(trade_plan.get('thesis', 'No thesis was generated.'))
        logger.info("Logging complete.")

    except (KrakenAPIError, DecisionEngineError) as e:
        logger.critical(f"A critical, module-specific error occurred: {e}")
    except Exception as e:
        logger.critical(f"An unexpected error occurred during the trading cycle: {e}", exc_info=True)
    
    logger.info("==========================================================")
    logger.info("✅ TRADING CYCLE COMPLETE ✅")
    logger.info("==========================================================")


def main():
    """
    Main function to set up the schedule and run the bot.
    """
    logger.info("Environment variables loaded.")

    # --- Schedule the Job ---
    # NOTE: The time is based on the server's local time.
    # For production, ensure the server is set to the desired timezone (e.g., MST for 07:00 MST).
    schedule.every().day.at("07:00").do(run_trading_cycle)
    
    logger.info("Trading bot scheduler started.")
    logger.info(f"The trading cycle is scheduled to run every day at 07:00 (server time).")
    
    # Run the bot once immediately on startup, then stick to the schedule
    logger.info("Performing initial run on startup...")
    run_trading_cycle()
    logger.info("Initial run complete. Now waiting for the next scheduled run.")

    while True:
        schedule.run_pending()
        time.sleep(60) # Check for a pending job every 60 seconds

if __name__ == "__main__":
    main()
