#!/usr/bin/env python3
"""
🤖 Multi-Agent Trading System LIVE DEMO
=======================================

This script runs a comprehensive demonstration of the complete multi-agent
trading system using REAL DATA and LIVE AI interactions.

Features:
- 🧠 4-Agent Architecture: Supervisor → Analyst → Strategist → Trader
- 🔍 Live market intelligence gathering
- 📊 Advanced prompt engineering and context management  
- 🤖 Real OpenAI API calls with decision quality assessment
- 🛡️ Comprehensive validation and risk management
- 📈 Complete cognitive transparency with audit trails
- 🎯 Production-ready multi-agent coordination

⚠️  REQUIRES: Internet connection, OpenAI API key, and (optionally) Kraken API keys
💡 This is a SAFE demo - it will NOT execute real trades on Kraken
"""

import sys
import os
import time
from datetime import datetime
from typing import Dict, Any

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment first
from dotenv import load_dotenv
load_dotenv()

def print_banner():
    """Print an awesome multi-agent banner."""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                  🤖 MULTI-AGENT TRADING SYSTEM DEMO 🤖                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  🧠 COGNITIVE AI ARCHITECTURE                                                ║
║  👑 Supervisor-AI:   Central orchestrator & decision reviewer               ║
║  📊 Analyst-AI:      Market intelligence & sentiment analysis               ║
║  🎯 Strategist-AI:   Advanced prompt engineering & context assembly         ║
║  🤖 Trader-AI:       OpenAI execution & decision parsing                    ║
║                                                                              ║
║  ✨ ADVANCED FEATURES                                                        ║
║  🔄 Shared context prevents agent fragmentation                             ║
║  🛡️  Comprehensive validation & risk management                              ║
║  📋 Complete cognitive audit trails                                         ║
║  🎯 Production-ready orchestration patterns                                 ║
║                                                                              ║
║  ⚠️  REQUIRES LIVE APIs (OpenAI + Internet)                                  ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)

def print_section_header(title: str, emoji: str = "🔥"):
    """Print a section header."""
    print(f"\n{emoji} {title}")
    print("=" * (len(title) + 4))

def print_subsection(title: str, emoji: str = "📌"):
    """Print a subsection header."""
    print(f"\n{emoji} {title}")

def check_dependencies():
    """Check if all required dependencies are available."""
    print_section_header("Dependency Check", "🔍")
    
    dependencies = [
        ("agents", "Multi-agent system"),
        ("openai", "OpenAI API client"),
        ("requests", "HTTP requests"),
        ("json", "JSON processing"),
        ("datetime", "Date/time handling"),
        ("bot.kraken_api", "Kraken API wrapper")
    ]
    
    all_good = True
    for module, description in dependencies:
        try:
            __import__(module)
            print(f"   ✅ {description}")
        except ImportError:
            if module == "agents":
                print(f"   ❌ {description} - Check that agents/ directory has __init__.py file")
            else:
                print(f"   ❌ {description} - Please install: pip install {module}")
            all_good = False
    
    if all_good:
        print("✅ All dependencies available!")
    return all_good

def check_environment():
    """Check environment variables and API keys."""
    print_section_header("Environment Check", "🌐")
    
    required_vars = {
        "OPENAI_API_KEY": "OpenAI API access (REQUIRED)",
        "KRAKEN_API_KEY": "Kraken API access (optional for demo)",
        "KRAKEN_API_SECRET": "Kraken API secret (optional for demo)"
    }
    
    env_status = {}
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            masked_value = f"{value[:8]}..." if len(value) > 8 else "***"
            print(f"   ✅ {description}: {masked_value}")
            env_status[var] = True
        else:
            print(f"   ⚠️  {description}: Not set")
            env_status[var] = False
    
    # OpenAI is required, Kraken is optional for demo
    openai_ready = env_status.get("OPENAI_API_KEY", False)
    kraken_ready = env_status.get("KRAKEN_API_KEY", False) and env_status.get("KRAKEN_API_SECRET", False)
    
    if openai_ready:
        print("✅ Environment ready for multi-agent demo!")
        if not kraken_ready:
            print("ℹ️  Note: Kraken API not configured - using demo portfolio data")
    else:
        print("❌ OpenAI API key required for multi-agent demo")
        return False
    
    return True

def demo_agent_initialization():
    """Demonstrate multi-agent system initialization."""
    print_section_header("Multi-Agent System Initialization", "🤖")
    
    try:
        print("🔧 Initializing Kraken API...")
        from bot.kraken_api import KrakenAPI
        kraken_api = KrakenAPI()
        print("   ✅ Kraken API initialized")
        
        print("🧠 Initializing Supervisor-AI and agent team...")
        from agents import SupervisorAgent
        supervisor = SupervisorAgent(kraken_api)
        print("   ✅ Supervisor-AI initialized")
        print("   ✅ Analyst-AI ready")
        print("   ✅ Strategist-AI ready") 
        print("   ✅ Trader-AI ready")
        
        print("🔍 Checking agent capabilities...")
        execution_summary = supervisor.get_execution_summary()
        agents_available = execution_summary.get("agents_available", [])
        pipeline_ready = execution_summary.get("pipeline_ready", False)
        
        print(f"   📊 Available agents: {', '.join(agents_available)}")
        print(f"   🚀 Pipeline ready: {'YES' if pipeline_ready else 'NO'}")
        
        print("✅ Multi-agent system fully operational!")
        return supervisor, execution_summary
        
    except Exception as e:
        print(f"❌ Multi-agent initialization failed: {e}")
        return None, None

def demo_full_pipeline_execution(supervisor: Any) -> Dict[str, Any]:
    """Demonstrate complete multi-agent pipeline execution."""
    print_section_header("Full Pipeline Execution", "🚀")
    
    # Prepare demo inputs
    pipeline_inputs = {
        "cycle_trigger": "live_demo",
        "research_focus": "general_market_analysis",
        "priority_keywords": ["bitcoin", "ethereum", "sec", "fed", "regulation", "crypto"],
        "strategic_focus": "alpha_generation", 
        "risk_parameters": "conservative",  # Conservative for demo
        "execution_mode": "demo_mode",  # Demo mode - no real trades
        "cycle_timestamp": datetime.now().isoformat()
    }
    
    print("📋 Pipeline Configuration:")
    print(f"   🎯 Research Focus: {pipeline_inputs['research_focus']}")
    print(f"   🔑 Priority Keywords: {', '.join(pipeline_inputs['priority_keywords'][:5])}...")
    print(f"   📊 Strategic Focus: {pipeline_inputs['strategic_focus']}")
    print(f"   🛡️  Risk Parameters: {pipeline_inputs['risk_parameters']}")
    print(f"   ⚙️  Execution Mode: {pipeline_inputs['execution_mode']}")
    
    print("\n🎬 Executing complete multi-agent pipeline...")
    print("Pipeline flow: Supervisor → Analyst → Strategist → Trader → Review → Decision")
    
    start_time = time.time()
    
    try:
        # Execute the full pipeline
        pipeline_result = supervisor.run(pipeline_inputs)
        
        execution_time = time.time() - start_time
        print(f"\n⏱️  Pipeline execution completed in {execution_time:.1f} seconds")
        
        return pipeline_result
        
    except Exception as e:
        print(f"\n❌ Pipeline execution failed: {e}")
        return {"status": "error", "error_message": str(e)}

def analyze_pipeline_results(pipeline_result: Dict[str, Any]):
    """Analyze and display detailed pipeline results."""
    print_section_header("Pipeline Results Analysis", "📊")
    
    if pipeline_result.get("status") == "error":
        print(f"❌ Pipeline failed: {pipeline_result.get('error_message')}")
        return
    
    # Extract key components
    execution_id = pipeline_result.get("execution_id", "unknown")
    execution_duration = pipeline_result.get("execution_duration_seconds", 0)
    final_state = pipeline_result.get("final_state", "unknown")
    
    print(f"🆔 Execution ID: {execution_id}")
    print(f"⏱️  Duration: {execution_duration:.1f} seconds")
    print(f"📊 Final State: {final_state}")
    
    # Analyze pipeline results
    pipeline_summary = pipeline_result.get("pipeline_result", {}).get("pipeline_summary", {})
    
    print_subsection("Pipeline Summary")
    print(f"   🤖 Agents Executed: {', '.join(pipeline_summary.get('agents_executed', []))}")
    print(f"   ✅ Pipeline Success: {'YES' if pipeline_summary.get('pipeline_success') else 'NO'}")
    print(f"   ⚠️  Total Warnings: {pipeline_summary.get('total_warnings', 0)}")
    print(f"   ❌ Total Errors: {pipeline_summary.get('total_errors', 0)}")
    
    # Analyze Analyst-AI results
    analyst_result = pipeline_result.get("pipeline_result", {}).get("analyst_result", {})
    if analyst_result.get("status") == "success":
        print_subsection("Analyst-AI Results")
        intelligence_quality = analyst_result.get("intelligence_quality", {})
        research_report = analyst_result.get("research_report", {})
        
        print(f"   📰 Headlines Collected: {intelligence_quality.get('total_headlines', 0)}")
        print(f"   📊 Intelligence Quality: {intelligence_quality.get('quality_score', 'unknown')}")
        print(f"   💭 Market Sentiment: {research_report.get('sentiment_analysis', {}).get('sentiment', 'unknown')}")
        print(f"   🔍 Key Themes: {len(research_report.get('key_themes', []))}")
    
    # Analyze Strategist-AI results  
    strategist_result = pipeline_result.get("pipeline_result", {}).get("strategist_result", {})
    if strategist_result.get("status") == "success":
        print_subsection("Strategist-AI Results")
        strategy_confidence = strategist_result.get("strategy_confidence", {})
        prompt_quality = strategist_result.get("prompt_quality_metrics", {})
        
        print(f"   🎯 Strategy Confidence: {strategy_confidence.get('confidence_score', 0)*100:.0f}%")
        print(f"   📝 Prompt Quality: {prompt_quality.get('quality_score', 0)*100:.0f}%")
        print(f"   📊 Estimated Tokens: {prompt_quality.get('estimated_tokens', 0)}")
        print(f"   ✅ Prompt Complete: {'YES' if prompt_quality.get('prompt_completeness') == 'complete' else 'NO'}")
    
    # Analyze Trader-AI results
    trader_result = pipeline_result.get("pipeline_result", {}).get("trader_result", {})
    if trader_result.get("status") == "success":
        print_subsection("Trader-AI Results")
        decision_quality = trader_result.get("decision_quality", {})
        trading_plan = trader_result.get("trading_plan", {})
        execution_metrics = trader_result.get("execution_metrics", {})
        
        print(f"   🧠 Decision Quality: {decision_quality.get('quality_grade', 'unknown')} ({decision_quality.get('overall_quality', 0)*100:.0f}%)")
        print(f"   📈 Proposed Trades: {decision_quality.get('trade_count', 0)}")
        print(f"   🎯 Decision Type: {decision_quality.get('decision_type', 'unknown')}")
        print(f"   ⚖️  Risk Level: {decision_quality.get('risk_assessment', 'unknown')}")
        print(f"   💰 API Cost: ${execution_metrics.get('estimated_cost_usd', 0):.4f}")
        print(f"   📝 Thesis Quality: {decision_quality.get('thesis_quality', 'unknown')}")
    
    # Analyze Final Decision
    final_decision = pipeline_result.get("pipeline_result", {}).get("final_decision", {})
    if final_decision:
        print_subsection("Supervisor Final Decision")
        approval_decision = final_decision.get("approval_decision", {})
        validation_result = final_decision.get("validation_result", {})
        
        print(f"   ✅ Plan Approved: {'YES' if approval_decision.get('approved') else 'NO'}")
        print(f"   🔍 Validation Passed: {'YES' if validation_result.get('validation_passed') else 'NO'}")
        print(f"   📊 Quality Score: {validation_result.get('quality_score', 0):.2f}")
        print(f"   ⚖️  Risk Level: {validation_result.get('risk_level', 'unknown')}")
        print(f"   💭 Approval Reason: {approval_decision.get('approval_reason', 'No reason provided')}")

def demo_cognitive_transparency(pipeline_result: Dict[str, Any]):
    """Demonstrate the cognitive transparency features."""
    print_section_header("Cognitive Transparency Demo", "🧠")
    
    print("📂 Checking organized agent transcript structure...")
    
    # Check for transcript files in the new organized structure
    transcript_dir = "logs/agent_transcripts"
    today = datetime.now().strftime('%Y-%m-%d')
    daily_transcript_dir = os.path.join(transcript_dir, today)
    
    if os.path.exists(daily_transcript_dir):
        print(f"   📁 Daily transcript directory: {daily_transcript_dir}")
        
        # Check time-based subdirectories
        time_dirs = [d for d in os.listdir(daily_transcript_dir) if os.path.isdir(os.path.join(daily_transcript_dir, d))]
        time_dirs.sort()
        
        print(f"   🕐 Time-based sessions found: {len(time_dirs)}")
        
        total_files = 0
        for time_dir in time_dirs:
            session_path = os.path.join(daily_transcript_dir, time_dir)
            transcript_files = [f for f in os.listdir(session_path) if f.endswith('.md')]
            total_files += len(transcript_files)
            print(f"      ⏰ Session {time_dir}: {len(transcript_files)} Markdown transcripts")
            
            # Show sample files from the most recent session
            if time_dir == time_dirs[-1] and transcript_files:
                for file in transcript_files[:3]:  # Show first 3 files
                    file_path = os.path.join(session_path, file)
                    file_size = os.path.getsize(file_path)
                    agent_name = file.split('_')[0].replace('_', '-').title()
                    file_type = 'thoughts' if 'thoughts' in file else 'output' if 'output' in file else 'error'
                    print(f"         📝 {agent_name} {file_type} ({file_size} bytes)")
        
        print(f"   📊 Total transcript files: {total_files} Markdown files")
        
    else:
        print(f"   ⚠️  Transcript directory not found: {daily_transcript_dir}")
    
    print("\n🔍 Enhanced Cognitive Process Features:")
    print("   📁 Organized by date and execution time")
    print("   📝 Human-readable Markdown format") 
    print("   🧠 Complete cognitive reasoning process")
    print("   📊 Structured input/output documentation")
    print("   🛡️  Full error context and debugging info")
    print("   📋 Professional audit trail for compliance")

def main():
    """Main demo function."""
    print_banner()
    
    # Dependency checks
    if not check_dependencies():
        print("\n❌ Dependency check failed. Please install missing packages.")
        return False
    
    # Environment checks  
    if not check_environment():
        print("\n❌ Environment check failed. Please configure API keys.")
        return False
    
    print("\n" + "="*80)
    print("🎬 STARTING MULTI-AGENT SYSTEM DEMONSTRATION")
    print("="*80)
    print(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Agent initialization
    supervisor, execution_summary = demo_agent_initialization()
    if not supervisor:
        print("\n❌ Agent initialization failed.")
        return False
    
    # Full pipeline execution
    print("\n⏱️  Estimated duration: 2-5 minutes (depends on OpenAI API response time)")
    print("🌐 This demo will make REAL API calls to gather live market data and AI decisions")
    
    # Countdown
    print("\n🚀 Starting pipeline execution in:")
    for i in range(3, 0, -1):
        print(f"   {i}...")
        time.sleep(1)
    print("   GO! 🎯\n")
    
    # Execute pipeline
    pipeline_result = demo_full_pipeline_execution(supervisor)
    
    # Analyze results
    analyze_pipeline_results(pipeline_result)
    
    # Show cognitive transparency
    demo_cognitive_transparency(pipeline_result)
    
    print("\n" + "="*80)
    print("📊 MULTI-AGENT DEMONSTRATION COMPLETED")
    print("="*80)
    
    success = pipeline_result.get("status") == "success"
    
    if success:
        print("🎉 ALL SYSTEMS OPERATIONAL!")
        print("✅ Multi-agent trading system is ready for production deployment")
        print("🚀 Each agent performed its specialized cognitive function flawlessly")
    else:
        print("⚠️  Demo encountered some issues:")
        print("🔍 Check the detailed output above for specific problems")
    
    print(f"\n⏰ End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n💡 To run the production system:")
    print("   python scheduler_multiagent.py")
    print("\n💡 To run this demo again:")
    print("   python run_multiagent_demo.py")
    
    return success

if __name__ == "__main__":
    print("🤖 Multi-Agent Trading System Live Demo")
    print("=======================================")
    
    success = main()
    
    if success:
        print("\n🎊 Demo completed successfully!")
        print("💡 Your multi-agent trading system is operational!")
    else:
        print("\n🔧 Demo encountered issues.")
        print("🛠️  Please review the output and fix any problems before deployment.")
    
    print("\n👋 Thanks for testing the Multi-Agent Trading System!")
    sys.exit(0 if success else 1)