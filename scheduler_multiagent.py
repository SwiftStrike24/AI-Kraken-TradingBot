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

# Set up logging to a file and to the console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/scheduler_multiagent.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
            "priority_keywords": ["bitcoin", "ethereum", "sec", "fed", "regulation"],
            "strategic_focus": "alpha_generation",
            "risk_parameters": "standard",
            "execution_mode": "live_trading",
            "cycle_timestamp": datetime.now().isoformat()
        }

        logger.info("🎯 Executing multi-agent trading pipeline...")
        logger.info("Pipeline stages: Analyst-AI → Strategist-AI → Trader-AI → Supervisor Review → Execution")

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
            total_errors = pipeline_summary.get("total_errors", 0)
            total_warnings = pipeline_summary.get("total_warnings", 0)
            
            if total_warnings > 0:
                logger.warning(f"⚠️  Pipeline completed with {total_warnings} warnings")
            if total_errors > 0:
                logger.error(f"❌ Pipeline completed with {total_errors} errors")
                
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
        logger.error(f"💥 Unexpected error in multi-agent trading cycle: {e}")
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

def main():
    """
    Main scheduler function for the multi-agent trading bot.
    """
    logger.info("🤖 Multi-Agent Trading Bot Scheduler Starting")
    logger.info("=" * 60)
    logger.info("Architecture: Supervisor-AI → [Analyst-AI, Strategist-AI, Trader-AI]")
    logger.info("Schedule: Daily at 07:00 MST")
    logger.info("Mode: Advanced Multi-Agent Cognitive System")
    logger.info("=" * 60)
    
    # Schedule the multi-agent trading cycle
    # Run every day at 07:00 MST
    schedule.every().day.at("07:00").do(run_multiagent_trading_cycle)
    
    logger.info("⏰ Scheduled daily multi-agent trading cycle for 07:00 MST")
    logger.info("🔄 Scheduler is now running. Press Ctrl+C to stop.")
    logger.info("")
    
    # Keep the scheduler running
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
            
    except KeyboardInterrupt:
        logger.info("👋 Multi-agent scheduler stopped by user")
    except Exception as e:
        logger.error(f"💥 Scheduler error: {e}")
    finally:
        logger.info("🏁 Multi-agent scheduler shutdown complete")

if __name__ == "__main__":
    # Option to run a demo or start the scheduler
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        run_multiagent_demo()
    else:
        main()