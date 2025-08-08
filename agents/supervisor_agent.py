"""
Supervisor Agent (Multi-Agent Orchestrator)

The Supervisor-AI is the central orchestrator that manages the entire multi-agent
trading pipeline. It ensures shared context between agents, handles failures gracefully,
and makes final decisions about trade execution.

This agent implements the centralized orchestration pattern recommended for
production multi-agent systems, avoiding the context fragmentation issues
that plague decentralized agent approaches.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

from .base_agent import BaseAgent
from .coingecko_agent import CoinGeckoAgent
from .analyst_agent import AnalystAgent
from .strategist_agent import StrategistAgent
from .trader_agent import TraderAgent
from .reflection_agent import ReflectionAgent

from bot.kraken_api import KrakenAPI
from bot.trade_executor import TradeExecutor
from bot.performance_tracker import PerformanceTracker

# logger = logging.getLogger(__name__)

class PipelineState(Enum):
    """Enumeration of possible pipeline states."""
    IDLE = "idle"
    RUNNING_REFLECTION = "running_reflection"
    RUNNING_COINGECKO = "running_coingecko"
    RUNNING_ANALYST = "running_analyst"
    RUNNING_STRATEGIST = "running_strategist"
    RUNNING_TRADER = "running_trader"
    REVIEWING_PLAN = "reviewing_plan"
    EXECUTING_TRADES = "executing_trades"
    COMPLETED = "completed"
    FAILED = "failed"
    # Add new state for iterative refinement
    REFINING_STRATEGY = "refining_strategy"

class SupervisorAgent(BaseAgent):
    """
    The Supervisor-AI orchestrates the entire multi-agent trading pipeline.
    
    This agent:
    1. Manages the execution flow of all other agents
    2. Ensures shared context between agents
    3. Handles failures and implements fallback strategies
    4. Makes final decisions about trade execution
    5. Maintains comprehensive audit trails
    """
    
    def __init__(self, kraken_api: KrakenAPI, logs_dir: str = "logs", max_refinement_loops: int = 2):
        """
        Initialize the Supervisor Agent.
        
        Args:
            kraken_api: Kraken API instance for trading operations
            logs_dir: Directory for saving agent transcripts
            max_refinement_loops: The maximum number of times the supervisor can loop back to refine a strategy.
        """
        # Create unified session directory for all agents in this trading cycle
        now = datetime.now()
        today = now.strftime('%Y-%m-%d')
        time_folder = now.strftime('%H-%M-%S')
        
        transcript_dir = os.path.join(logs_dir, "agent_transcripts")
        daily_dir = os.path.join(transcript_dir, today)
        session_dir = os.path.join(daily_dir, time_folder)
        os.makedirs(session_dir, exist_ok=True)
        
        # Initialize supervisor with the session directory
        super().__init__("Supervisor-AI", logs_dir, session_dir)
        
        self.kraken_api = kraken_api
        self.logs_dir = logs_dir
        self.unified_session_dir = session_dir
        
        # Initialize execution components
        self.trade_executor = TradeExecutor(kraken_api)
        self.performance_tracker = PerformanceTracker(kraken_api, logs_dir)
        
        # Initialize agent team with unified session directory
        self.reflection = ReflectionAgent(logs_dir, session_dir)
        self.coingecko = CoinGeckoAgent(logs_dir, session_dir)
        self.analyst = AnalystAgent(logs_dir, session_dir)
        self.strategist = StrategistAgent(kraken_api, logs_dir, session_dir)
        self.trader = TraderAgent(logs_dir, session_dir)
        
        # Pipeline state tracking
        self.current_state = PipelineState.IDLE
        self.execution_context = {}
        self.max_refinement_loops = max_refinement_loops
        self.refinement_attempts = 0
        
        self.logger.info(f"Supervisor-AI initialized with unified session: {session_dir}")
        self.logger.info("Complete agent team initialized with shared session directory")
    
    def _execute_with_fallback(self, agent_fn, fallback_fn, agent_name: str, *args, **kwargs):
        """
        Executes an agent's function with a fallback mechanism.

        Args:
            agent_fn: The primary function to execute for the agent.
            fallback_fn: The fallback function to execute on failure.
            agent_name: The name of the agent for logging.
            *args, **kwargs: Arguments to pass to the agent function.

        Returns:
            The result of either the agent function or the fallback function.
        """
        try:
            return agent_fn(*args, **kwargs)
        except Exception as e:
            # --- NEW: CIRCUIT BREAKER for fatal errors ---
            error_str = str(e).lower()
            if "context_length_exceeded" in error_str or "invalid_request_error" in error_str:
                self.logger.critical(f"🔥 FATAL ERROR in {agent_name}: {e}", exc_info=True)
                self.logger.critical("   This is a non-recoverable error. The prompt is too long for the AI model.")
                self.logger.critical("   The trading cycle will be aborted to prevent further errors.")
                # Re-raise the exception to be caught by the top-level handler and stop the scheduler
                raise e

            self.logger.error(f"🚨 {agent_name} failed: {e}", exc_info=True)
            self.execution_context["errors"].append(f"{agent_name} failed: {str(e)}")
            self.logger.warning(f"🛡️  Executing fallback for {agent_name}...")
            return fallback_fn()

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the complete multi-agent trading pipeline.
        
        Args:
            inputs: Initial directives and configuration for the trading cycle
            
        Returns:
            Complete pipeline execution results
        """
        self.logger.info("🚀 Beginning multi-agent trading pipeline execution")
        
        execution_id = f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()
        
        # Initialize execution context
        self.execution_context = {
            "execution_id": execution_id,
            "start_time": start_time.isoformat(),
            "inputs": inputs,
            "agent_outputs": {},
            "pipeline_state": PipelineState.IDLE.value,
            "errors": [],
            "warnings": [],
            "refinement_history": [] # To track refinement loops
        }
        self.refinement_attempts = 0 # Reset attempts for each new execution
        
        try:
            # Execute the complete pipeline
            pipeline_result = self._execute_pipeline_loop(inputs)
            
            end_time = datetime.now()
            execution_duration = (end_time - start_time).total_seconds()
            
            return {
                "status": "success",
                "agent": "Supervisor-AI",
                "execution_id": execution_id,
                "timestamp": end_time.isoformat(),
                "execution_duration_seconds": execution_duration,
                "pipeline_result": pipeline_result,
                "execution_context": self.execution_context,
                "final_state": self.current_state.value
            }
            
        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {e}")
            self.current_state = PipelineState.FAILED
            
            return {
                "status": "error",
                "agent": "Supervisor-AI",
                "execution_id": execution_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "execution_context": self.execution_context,
                "final_state": self.current_state.value
            }
    
    def _execute_pipeline_loop(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the multi-agent pipeline as a state-driven loop, allowing for iterative refinement.
        """
        # --- FIX: Ensure fresh data on the first run of the cycle ---
        inputs['bypass_cache'] = True 
        
        # --- NEW: REFLECTION STAGE ---
        reflection_result = self._run_reflection_stage(inputs)
        
        # Make reflection available to Analyst/Research for report augmentation
        try:
            from .reflection_agent import REFLECTION_PROVIDER
            
            reflection_model_name = "Unknown"
            if REFLECTION_PROVIDER == "openai":
                from bot.openai_config import get_default_openai_model
                model_id = get_default_openai_model()
                if "gpt-5" in model_id:
                    reflection_model_name = "OpenAI GPT-5"
                else:
                    reflection_model_name = f"OpenAI {model_id}"
            
            elif REFLECTION_PROVIDER == "gemini":
                from bot.gemini_client import DEFAULT_MODEL as GEMINI_MODEL_NAME
                reflection_model_name = f"Google {GEMINI_MODEL_NAME}"

            inputs["reflection_report"] = reflection_result.get("reflection_report", {})
            inputs["reflection_model"] = reflection_model_name
        except Exception as e:
            self.logger.warning(f"Could not set reflection model name: {e}")
            # Fallback for safety
            inputs["reflection_report"] = reflection_result.get("reflection_report", {})
            inputs["reflection_model"] = "gemini-2.5-pro"

        # Initial data gathering stages
        coingecko_result = self._run_coingecko_stage(inputs)
        analyst_result = self._run_analyst_stage(coingecko_result, inputs)
        # Keep the initial analyst report available for reuse during fast refinement
        initial_analyst_result = analyst_result

        while self.refinement_attempts < self.max_refinement_loops:
            self.current_state = PipelineState.RUNNING_STRATEGIST
            strategist_result = self._execute_with_fallback(
                agent_fn=self._run_strategist_stage,
                fallback_fn=self._strategist_fallback,
                agent_name="Strategist-AI",
                analyst_result=analyst_result,
                coingecko_result=coingecko_result,
                reflection_result=reflection_result, # Pass reflection report
                inputs=inputs
            )
            if strategist_result.get("status") == "critical_failure":
                self.current_state = PipelineState.FAILED
                return {"pipeline_summary": self._generate_pipeline_summary()}

            trader_result = self._execute_with_fallback(
                agent_fn=self._run_trader_stage,
                fallback_fn=self._trader_fallback,
                agent_name="Trader-AI",
                strategist_result=strategist_result,
                inputs=inputs
            )

            final_decision = self._review_trading_plan(trader_result)

            # --- QUALITY GATE & DYNAMIC REFINEMENT LOOP ---
            if self._should_refine_strategy(final_decision):
                self.refinement_attempts += 1
                self.current_state = PipelineState.REFINING_STRATEGY
                # --- ENHANCED LOGGING (Phase 1) ---
                rejection_reason = final_decision['approval_decision'].get('approval_reason', 'No reason specified')
                self.logger.warning(f"🤔 Strategy rejected. Attempting refinement loop {self.refinement_attempts}/{self.max_refinement_loops}...")
                self.logger.warning(f"   REASON: {rejection_reason}")
                
                refinement_log = {
                    "attempt": self.refinement_attempts,
                    "reason": rejection_reason,
                    "original_thesis": trader_result.get("trading_plan", {}).get("thesis")
                }

                # Decide whether to fast-skip research refetch
                refinement_query = self._create_refinement_query(trader_result, final_decision.get("validation_result", {}).get("validation_issues", []))
                fast_refinement = inputs.get("fast_refinement", True)
                # Force fresh research when the issue is minimum volume, otherwise reuse
                volume_issue = any("Volume below minimum" in issue for issue in final_decision.get("validation_result", {}).get("validation_issues", []))
                if fast_refinement and not volume_issue:
                    self.logger.info("Fast refinement enabled: reusing prior Analyst-AI data, skipping RSS refetch")
                    refinement_log["skipped_refetch"] = True
                    refinement_log["new_analyst_focus"] = refinement_query
                    self.execution_context["refinement_history"].append(refinement_log)
                else:
                    # Delegate new task to Analyst for more data
                    self.logger.info("Delegating new task to Analyst-AI for more targeted research (cache bypassed)...")
                    self.logger.info(f"   REFINEMENT QUERY: {refinement_query}")
                    refined_analyst_inputs = inputs.copy()
                    refined_analyst_inputs['research_focus'] = refinement_query
                    # Force cache bypass during refinement to get fresh data
                    refined_analyst_inputs['bypass_cache'] = True 
                    analyst_result = self._run_analyst_stage(coingecko_result, refined_analyst_inputs)
                    refinement_log["new_analyst_focus"] = refinement_query
                    refinement_log["new_analyst_result"] = analyst_result.get("research_report", {}).get("market_context")
                    self.execution_context["refinement_history"].append(refinement_log)
                
                # Add the specific failure reason as context for the next attempt
                inputs['refinement_context'] = f"The previous plan was rejected for the following reason: '{rejection_reason}'. You MUST address this issue in your new plan."
                
                continue # Loop back to the strategist with the (possibly reused) analyst data

            # If the plan is approved, break the loop and proceed to execution.
            break

        # --- NEW: CIRCUIT BREAKER / FALLBACK STRATEGY (Phase 2) ---
        if self.refinement_attempts >= self.max_refinement_loops and self._should_refine_strategy(final_decision):
            self.logger.error(f"❌ Maximum refinement loops ({self.max_refinement_loops}) reached. No valid plan could be generated.")
            self.logger.warning("🛡️  FALLBACK: Defaulting to a DEFENSIVE_HOLDING strategy to ensure safe cycle completion.")
            
            # Create a safe, 'hold' fallback plan
            last_rejection_reason = final_decision['approval_decision'].get('approval_reason', 'Unknown validation issue')
            fallback_thesis = f"The AI failed to generate a valid trading plan after {self.max_refinement_loops} attempts. The last rejected plan had the following issue(s): '{last_rejection_reason}'. As a safety measure, the system is defaulting to a defensive hold strategy to preserve capital. No trades will be executed. The system will try again in the next cycle."
            
            final_decision['trading_plan'] = {
                "trades": [],
                "strategy": "DEFENSIVE_HOLDING",
                "thesis": fallback_thesis
            }
            # Approve the fallback plan for execution (which does nothing but logs the new thesis)
            final_decision['approval_decision']['approved'] = True
            final_decision['approval_decision']['approval_reason'] = "Fallback defensive hold strategy activated after refinement failure."


        # --- EXECUTION STAGE ---
        execution_result = self._execute_trades_if_approved(final_decision)
        tracking_result = self._update_performance_tracking(execution_result)
        
        return {
            "reflection_result": reflection_result,
            "coingecko_result": coingecko_result,
            "analyst_result": initial_analyst_result,
            "strategist_result": strategist_result,
            "trader_result": trader_result,
            "final_decision": final_decision,
            "execution_result": execution_result,
            "tracking_result": tracking_result,
            "pipeline_summary": self._generate_pipeline_summary()
        }

    def _should_refine_strategy(self, final_decision: Dict[str, Any]) -> bool:
        """
        Determines if the trading plan is good enough or needs another refinement loop.
        """
        approval_decision = final_decision.get("approval_decision", {})
        validation_result = final_decision.get("validation_result", {})

        # If it's already approved, no refinement needed.
        if approval_decision.get("approved", False):
            return False
        
        # If there are hard validation issues, refinement won't help, so don't loop.
        # --- PHASE 1 ENHANCEMENT: Allow refinement for certain validation issues ---
        validation_result = final_decision.get("validation_result", {})
        if not validation_result.get("validation_passed", False):
            # Check if the failure is something refineable, like a minimum volume issue.
            issues = validation_result.get("validation_issues", [])
            is_refineable = any(("Volume below minimum" in issue) or ("USD value below effective minimum" in issue) for issue in issues)
            if is_refineable:
                return True # This is a key fix: explicitly trigger refinement for this error type
            if not is_refineable:
                return False # Don't loop for non-refineable issues like invalid format

        # Refine if the quality score is too low or risk is too high without justification.
        if "Quality score too low" in approval_decision.get("approval_reason", ""):
            return True
        if "High risk with insufficient quality" in approval_decision.get("approval_reason", ""):
            return True

        return False

    def _create_refinement_query(self, trader_result: Dict[str, Any], validation_issues: List[str] = None) -> str:
        """
        Creates a targeted research query for the Analyst-AI based on a rejected trade plan.
        """
        trading_plan = trader_result.get("trading_plan", {})
        trades = trading_plan.get("trades", [])
        
        # If the rejection was due to a specific validation issue, address it.
        if validation_issues:
            # Focus on the first issue for simplicity
            issue = validation_issues[0]
            if "Volume below minimum" in issue:
                # E.g., "Trade 1: Volume below minimum. Calculated 1.33186999, requires 2.00000000 for XXRPZUSD"
                parts = issue.split(' ')
                try:
                    # Correctly parse the components from the error string
                    asset_name = parts[-1]
                    # Find the indices for calculated and required volumes
                    calculated_idx = parts.index("Calculated") + 1
                    requires_idx = parts.index("requires") + 1
                    
                    calculated_vol = parts[calculated_idx].replace(',', '')
                    required_vol = parts[requires_idx].replace(',', '')
                    
                    # Get portfolio value to add more context
                    portfolio_value = self._get_portfolio_value()

                    return f"The previous trading plan for {asset_name} was rejected. The calculated trade volume of {calculated_vol} was below the required minimum of {required_vol}. For our small portfolio of ${portfolio_value:.2f}, this is a common issue. Propose a new plan with a DIFFERENT asset or a significantly HIGHER allocation to an existing one to meet the minimums. Do not propose a trade for {asset_name} again in this refinement loop unless you dramatically increase its allocation to meet the minimum."
                except (IndexError, ValueError) as e:
                     self.logger.error(f"Error parsing validation issue string for refinement query: '{issue}'. Error: {e}")
                     return f"The previous plan was rejected due to a trade being too small. Propose a new plan with a different asset or a higher allocation to meet minimum order sizes."

        if not trades:
            return "General market analysis, with a focus on identifying any high-conviction opportunities missed."

        # Focus on the assets in the rejected plan
        assets = [t.get('pair', '').replace('USD', '').replace('ZUSD', '').replace('XBT','BTC') for t in trades]
        unique_assets = list(set(assets))

        query = f"The previous trading plan was rejected for low confidence. Conduct a deep dive on the following assets: {', '.join(unique_assets)}. Focus on finding recent (last 24 hours) news, on-chain data, or sentiment shifts that either strongly support or strongly contradict a trade. Ignore general market news and provide only specific, actionable intelligence on these assets."
        return query

    def _run_reflection_stage(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the Reflection-AI stage of the pipeline.
        
        Args:
            inputs: Initial pipeline inputs
            
        Returns:
            Reflection execution results
        """
        self.logger.info("🧠 Stage 0: Running Historical Reflection Analysis")
        self.current_state = PipelineState.RUNNING_REFLECTION
        
        try:
            reflection_result = self.reflection.run(inputs)
            self.execution_context["agent_outputs"]["reflection"] = reflection_result
            
            if reflection_result.get("status") == "error":
                self.execution_context["warnings"].append(f"Reflection-AI failed: {reflection_result.get('error_message')}")
                return self._reflection_fallback()
            
            self.logger.info("✅ Reflection-AI completed successfully")
            return reflection_result
            
        except Exception as e:
            self.logger.error(f"Reflection stage failed critically: {e}", exc_info=True)
            self.execution_context["warnings"].append(f"Reflection stage failed critically: {str(e)}")
            return self._reflection_fallback()

    def _reflection_fallback(self):
        """Fallback for Reflection-AI."""
        self.logger.warning("Executing Reflection-AI fallback: No historical context will be available.")
        return {"status": "fallback", "reflection_report": {"summary": "Historical reflection is unavailable due to an agent failure."}}

    def _run_coingecko_stage(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the CoinGecko-AI stage of the pipeline.
        
        Args:
            inputs: Initial pipeline inputs
            
        Returns:
            CoinGecko execution results
        """
        self.logger.info("💰 Stage 1: Running CoinGecko Market Data Collection")
        self.current_state = PipelineState.RUNNING_COINGECKO
        
        try:
            # Prepare CoinGecko inputs
            coingecko_inputs = {
                "token_ids": inputs.get("token_ids", ['bitcoin', 'ethereum', 'solana', 'cardano', 'ripple', 'sui', 'ethena', 'dogecoin', 'fartcoin', 'bonk']),
                "include_trending": inputs.get("include_trending", True),
                "vs_currency": inputs.get("vs_currency", "usd"),
                "supervisor_directives": inputs
            }
            
            # Execute CoinGecko agent
            coingecko_result = self.coingecko.run(coingecko_inputs)
            
            # Store result in execution context
            self.execution_context["agent_outputs"]["coingecko"] = coingecko_result
            
            if coingecko_result.get("status") == "error":
                self.execution_context["warnings"].append(f"CoinGecko-AI failed, proceeding with no market data: {coingecko_result.get('error_message')}")
                return self._coingecko_fallback()
            
            self.logger.info("✅ CoinGecko-AI completed successfully")
            return coingecko_result
            
        except Exception as e:
            self.logger.error(f"CoinGecko stage failed: {e}", exc_info=True)
            self.execution_context["warnings"].append(f"CoinGecko stage failed critically: {str(e)}")
            return self._coingecko_fallback()
    
    def _coingecko_fallback(self):
        """Fallback for CoinGecko-AI."""
        self.logger.warning("Executing CoinGecko-AI fallback: No market data will be available.")
        return {"status": "fallback", "market_data": {}, "trending_data": {}, "data_quality": {"quality_score": "degraded"}}

    def _run_analyst_stage(self, coingecko_result: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the Analyst-AI stage of the pipeline.
        
        Args:
            coingecko_result: Results from the CoinGecko-AI stage
            inputs: Initial pipeline inputs
            
        Returns:
            Analyst execution results
        """
        self.logger.info("📊 Stage 2: Running Market Intelligence Analysis")
        self.current_state = PipelineState.RUNNING_ANALYST
        
        try:
            # Prepare analyst inputs with CoinGecko data
            analyst_inputs = {
                "research_focus": inputs.get("research_focus", "general_market_analysis"),
                "priority_keywords": inputs.get("priority_keywords", []),
                "supervisor_directives": inputs,
                "coingecko_data": coingecko_result,  # Pass the full CoinGecko data
                "bypass_cache": inputs.get("bypass_cache", False),  # Pass the flag through
                "reflection_report": inputs.get("reflection_report"),
                "reflection_model": inputs.get("reflection_model"),
                "coingecko_execution_context": {
                    "timestamp": coingecko_result.get("timestamp"),
                    "quality": coingecko_result.get("data_quality", {}),
                    "data_freshness": "live"
                }
            }
            
            # Execute analyst
            analyst_result = self.analyst.run(analyst_inputs)
            
            # Store result in execution context
            self.execution_context["agent_outputs"]["analyst"] = analyst_result
            
            if analyst_result.get("status") == "error":
                self.execution_context["warnings"].append(f"Analyst-AI failed, proceeding with no news data: {analyst_result.get('error_message')}")
                return self._analyst_fallback()
            
            self.logger.info("✅ Analyst-AI completed successfully")
            return analyst_result
            
        except Exception as e:
            self.logger.error(f"Analyst stage failed: {e}", exc_info=True)
            self.execution_context["warnings"].append(f"Analyst stage failed critically: {str(e)}")
            return self._analyst_fallback()
    
    def _analyst_fallback(self):
        """Fallback for Analyst-AI."""
        self.logger.warning("Executing Analyst-AI fallback: No news/market intelligence will be available.")
        return {"status": "fallback", "research_report": {"market_summary": "Market intelligence unavailable due to agent failure."}}
    
    def _run_strategist_stage(self, analyst_result: Dict[str, Any], coingecko_result: Dict[str, Any], reflection_result: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the Strategist-AI stage of the pipeline.
        
        Args:
            analyst_result: Results from the Analyst-AI
            coingecko_result: Results from the CoinGecko-AI
            reflection_result: Results from the Reflection-AI
            inputs: Original pipeline inputs
            
        Returns:
            Strategist execution results
        """
        self.logger.info("🧠 Stage 3: Running Strategic Prompt Construction")
        self.current_state = PipelineState.RUNNING_STRATEGIST
        
        try:
            # Prepare strategist inputs with shared context
            strategist_inputs = {
                "reflection_report": reflection_result.get("reflection_report", {}),
                "research_report": analyst_result.get("research_report", {}),
                "intelligence_quality": analyst_result.get("intelligence_quality", {}),
                "coingecko_data": coingecko_result.get("market_data", {}),
                "trending_data": coingecko_result.get("trending_data", {}),
                "coingecko_quality": coingecko_result.get("data_quality", {}),
                "supervisor_directives": inputs,
                "analyst_execution_context": {
                    "timestamp": analyst_result.get("timestamp"),
                    "quality": analyst_result.get("intelligence_quality", {}).get("quality_score", "unknown")
                },
                "coingecko_execution_context": {
                    "timestamp": coingecko_result.get("timestamp"),
                    "quality": coingecko_result.get("data_quality", {}).get("quality_score", "unknown")
                }
            }
            
            # Execute strategist
            strategist_result = self.strategist.run(strategist_inputs)
            
            # Store result in execution context
            self.execution_context["agent_outputs"]["strategist"] = strategist_result
            
            if strategist_result.get("status") == "error":
                self.execution_context["errors"].append(f"Strategist-AI failed: {strategist_result.get('error_message')}")
                raise Exception(f"Strategic prompt construction failed: {strategist_result.get('error_message')}")
            
            self.logger.info("✅ Strategist-AI completed successfully")
            return strategist_result
            
        except Exception as e:
            self.logger.error(f"Strategist stage failed: {e}", exc_info=True)
            self.execution_context["errors"].append(f"Strategist stage failure: {str(e)}")
            raise

    def _strategist_fallback(self):
        """Fallback for Strategist-AI."""
        self.logger.critical("Executing Strategist-AI fallback: Aborting trading cycle.")
        return {"status": "critical_failure", "prompt_payload": None}
    
    def _run_trader_stage(self, strategist_result: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the Trader-AI stage of the pipeline.
        
        Args:
            strategist_result: Results from the Strategist-AI
            inputs: Original pipeline inputs
            
        Returns:
            Trader execution results
        """
        self.logger.info("🤖 Stage 4: Running AI Trading Decision Generation")
        self.current_state = PipelineState.RUNNING_TRADER
        
        try:
            # Prepare trader inputs with shared context
            trader_inputs = {
                "prompt_payload": strategist_result.get("prompt_payload", {}),
                "strategy_confidence": strategist_result.get("strategy_confidence", {}),
                "supervisor_directives": inputs,
                "upstream_context": {
                    "analyst_timestamp": self.execution_context["agent_outputs"]["analyst"].get("timestamp"),
                    "strategist_timestamp": strategist_result.get("timestamp"),
                    "prompt_quality": strategist_result.get("prompt_quality_metrics", {}).get("quality_score", 0)
                }
            }
            
            # Execute trader
            trader_result = self.trader.run(trader_inputs)
            
            # Store result in execution context
            self.execution_context["agent_outputs"]["trader"] = trader_result
            
            if trader_result.get("status") == "error":
                self.execution_context["errors"].append(f"Trader-AI failed: {trader_result.get('error_message')}")
                raise Exception(f"AI trading decision generation failed: {trader_result.get('error_message')}")
            
            self.logger.info("✅ Trader-AI completed successfully")
            return trader_result
            
        except Exception as e:
            self.logger.error(f"Trader stage failed: {e}", exc_info=True)
            self.execution_context["errors"].append(f"Trader stage failure: {str(e)}")
            raise

    def _trader_fallback(self):
        """Fallback for Trader-AI."""
        self.logger.warning("Executing Trader-AI fallback: Defaulting to DEFENSIVE_HOLDING strategy.")
        return {
            "status": "fallback",
            "trading_plan": {
                "trades": [],
                "strategy": "DEFENSIVE_HOLDING",
                "thesis": "AI decision engine failed. Defaulting to a defensive hold strategy to preserve capital. No trades will be executed."
            },
            "decision_quality": {"quality_grade": "degraded"}
        }
    
    def _review_trading_plan(self, trader_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Review the final trading plan and make approval decisions.
        
        Args:
            trader_result: Results from the Trader-AI
            
        Returns:
            Final decision with approval status
        """
        self.logger.info("🔍 Stage 5: Reviewing Trading Plan")
        self.current_state = PipelineState.REVIEWING_PLAN
        
        trading_plan = trader_result.get("trading_plan", {})
        decision_quality = trader_result.get("decision_quality", {})
        
        # Perform supervisor-level validation
        validation_result = self._validate_trading_plan(trading_plan, decision_quality)
        
        # Make final approval decision
        approval_decision = self._make_approval_decision(validation_result, trading_plan)
        
        review_result = {
            "validation_result": validation_result,
            "approval_decision": approval_decision,
            "trading_plan": trading_plan,
            "supervisor_reasoning": self._generate_supervisor_reasoning(validation_result, approval_decision),
            "review_timestamp": datetime.now().isoformat()
        }
        
        # Store in execution context
        self.execution_context["final_review"] = review_result
        
        self.logger.info(f"✅ Trading plan review completed - Decision: {approval_decision['approved']}")
        return review_result
    
    def _normalize_pair(self, pair: str) -> Optional[str]:
        """
        Cleans and standardizes a trading pair string to find the official Kraken pair name.
        
        Args:
            pair: The trading pair string from the AI's plan.
            
        Returns:
            A standardized, valid Kraken pair name or None if not found.
        """
        # Clean the input
        clean_pair = pair.upper().replace('/', '').replace('-', '')
        
        # Handle specific asset mappings like BTC -> XBT
        if clean_pair.startswith('BTC'):
            clean_pair = 'XBT' + clean_pair[3:]

        # For pairs ending in USD, try to find the exact Kraken pair name
        if clean_pair.endswith('USD'):
            base_asset = clean_pair[:-3] # Remove 'USD'
            
            # Check for direct mapping (e.g., 'ETH' -> 'XETHZUSD')
            # Note: asset_to_usd_pair_map uses clean asset names (without X/Z prefixes)
            if base_asset in self.kraken_api.asset_to_usd_pair_map:
                return self.kraken_api.asset_to_usd_pair_map[base_asset]
            
            # Fallback: check for prefixed versions (e.g., 'XETH' -> 'XETHZUSD')
            for prefix in ['X', 'Z']:
                if base_asset.startswith(prefix) and base_asset[1:] in self.kraken_api.asset_to_usd_pair_map:
                    return self.kraken_api.asset_to_usd_pair_map[base_asset[1:]]

        # If it's already a valid pair name, return it
        if pair in self.kraken_api.asset_pairs:
            return pair
            
        self.logger.warning(f"Could not normalize or find pair: {pair}")
        return None

    def _validate_trading_plan(self, trading_plan: Dict[str, Any], quality_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive validation of the trading plan.
        
        Args:
            trading_plan: The trading plan from Trader-AI
            quality_metrics: Quality assessment from Trader-AI
            
        Returns:
            Validation results
        """
        validation_issues = []
        validation_warnings = []
        
        # Check 1: Plan structure validation
        if "trades" not in trading_plan or not isinstance(trading_plan.get("trades"), list):
            validation_issues.append("Trading plan missing or invalid trades list")
        
        if not trading_plan.get("thesis") or not isinstance(trading_plan.get("thesis"), str):
            validation_issues.append("Trading plan missing or invalid thesis")
        
        # Check 2: Quality thresholds
        overall_quality = quality_metrics.get("overall_quality", 0)
        if overall_quality < 0.5:
            validation_warnings.append(f"Low decision quality score: {overall_quality}")
        
        # Check 3: Risk assessment
        risk_level = quality_metrics.get("risk_assessment", "unknown")
        if risk_level == "high":
            validation_warnings.append("High risk level detected in trading plan")
        
        # Check 4: Trade count sanity check
        trades = trading_plan.get("trades", [])
        if len(trades) > 5:
            validation_warnings.append(f"Unusually high number of trades: {len(trades)}")
        
        # --- PHASE 1 ENHANCEMENT: Pre-Execution Volume Validation ---
        # Get portfolio value once for all calculations
        portfolio_value = self._get_portfolio_value()

        # Check 5: Confidence-based validation for new percentage trades
        for i, trade in enumerate(trades):
            if 'confidence_score' in trade:
                confidence = trade.get('confidence_score', 0)
                allocation = trade.get('allocation_percentage', 0)
                
                # Validate confidence score range
                if not (0.1 <= confidence <= 1.0):
                    validation_issues.append(f"Trade {i+1}: Invalid confidence score {confidence} (must be 0.1-1.0)")
                
                # Portfolio-size-aware allocation validation (matching Trader-AI logic)
                try:
                    # Get current portfolio value for validation
                    # portfolio_value = self._get_portfolio_value() # Moved up
                    max_allocation = 0.95 if portfolio_value < 50 else 0.4
                    
                    # Allow sell orders to exceed the max allocation for rebalancing
                    if trade.get('action') == 'sell':
                        if not (0.01 <= allocation <= 1.0): # Allow up to 100% for sells
                            validation_issues.append(f"Trade {i+1}: Invalid sell allocation {allocation*100:.1f}% (must be 1-100%)")
                    else: # Buy orders
                        if not (0.01 <= allocation <= max_allocation):
                            if portfolio_value < 50:
                                validation_issues.append(f"Trade {i+1}: Invalid allocation {allocation*100:.1f}% (must be 1-95% for small portfolios <$50)")
                            else:
                                validation_issues.append(f"Trade {i+1}: Invalid allocation {allocation*100:.1f}% (must be 1-40% for portfolios >$50)")
                except Exception as e:
                    # Fallback to 40% limit if portfolio value can't be determined
                    self.logger.warning(f"Could not determine portfolio value for validation: {e}")
                    if not (0.01 <= allocation <= 0.4):
                        validation_issues.append(f"Trade {i+1}: Invalid allocation {allocation*100:.1f}% (must be 1-40%)")
                
                # Check confidence-allocation alignment
                if confidence < 0.5 and allocation > 0.2:
                    validation_warnings.append(f"Trade {i+1}: High allocation ({allocation*100:.1f}%) with low confidence ({confidence:.2f})")
                
                # Check for very low confidence trades
                if confidence < 0.3:
                    validation_warnings.append(f"Trade {i+1}: Very low confidence score ({confidence:.2f})")
        
                # Check 6: Pre-execution volume validation
                try:
                    normalized_pair = self._normalize_pair(trade.get('pair', ''))
                    if not normalized_pair:
                        validation_issues.append(f"Trade {i+1}: Invalid or unknown pair '{trade.get('pair')}'")
                        continue

                    pair_details = self.kraken_api.get_pair_details(normalized_pair)
                    if not pair_details:
                        validation_issues.append(f"Trade {i+1}: Could not fetch trading rules for pair '{normalized_pair}'")
                        continue
                    
                    min_volume = float(pair_details.get('ordermin', 0))
                    costmin = float(pair_details.get('costmin', 0) or 0.0)
                    
                    # Calculate expected volume from allocation
                    if trade.get('action') == 'sell':
                        # For sells, the volume is based on the existing holding's value
                        base_asset_clean = pair_details.get('base', '')
                        if base_asset_clean.startswith(('X', 'Z')) and len(base_asset_clean) > 1:
                            base_asset_clean = base_asset_clean[1:]

                        portfolio_context = self.kraken_api.get_comprehensive_portfolio_context()
                        holding_amount = portfolio_context['raw_balances'].get(base_asset_clean, 0.0)
                        calculated_volume = holding_amount * allocation
                    else: # buy
                        prices = self.kraken_api.get_ticker_prices([normalized_pair])
                        current_price = prices[normalized_pair]['price']
                        usd_amount = portfolio_value * allocation
                        calculated_volume = usd_amount / current_price if current_price > 0 else 0

                    if calculated_volume < min_volume:
                        validation_issues.append(f"Trade {i+1}: Volume below minimum. Calculated {calculated_volume:.8f}, requires {min_volume:.8f} for {trade.get('pair')}")

                    # Effective USD minimum check using live price
                    try:
                        prices = self.kraken_api.get_ticker_prices([normalized_pair])
                        price_for_min = prices.get(normalized_pair, {}).get('price', 0)
                        trade_usd_value = calculated_volume * price_for_min if price_for_min else 0.0
                        effective_min_usd = max(costmin, min_volume * price_for_min if price_for_min else 0.0)
                        if effective_min_usd > 0 and trade_usd_value < effective_min_usd:
                            validation_issues.append(
                                f"Trade {i+1}: USD value below effective minimum. Calculated ${trade_usd_value:.2f}, requires ${effective_min_usd:.2f} for {trade.get('pair')}"
                            )
                    except Exception:
                        pass
 
                except Exception as e:
                    validation_warnings.append(f"Trade {i+1}: Could not perform volume pre-validation: {e}")


        # Check 7: Thesis quality
        thesis_quality = quality_metrics.get("thesis_quality", "unknown")
        if thesis_quality == "brief":
            validation_warnings.append("Brief thesis may indicate insufficient reasoning")
        
        validation_passed = len(validation_issues) == 0
        
        return {
            "validation_passed": validation_passed,
            "validation_issues": validation_issues,
            "validation_warnings": validation_warnings,
            "quality_score": overall_quality,
            "risk_level": risk_level,
            "trade_count": len(trades),
            "thesis_quality": thesis_quality
        }
    
    def _get_portfolio_value(self) -> float:
        """
        Get the current portfolio value in USD using the canonical method.
        """
        try:
            # Use the single source of truth for portfolio valuation.
            # This method correctly handles asset normalization (e.g., ETH.F) and dust.
            portfolio_context = self.kraken_api.get_comprehensive_portfolio_context()
            return portfolio_context.get('total_equity', 0.0)
        except Exception as e:
            self.logger.error(f"Critical error calculating portfolio value: {e}", exc_info=True)
            # Fallback to a value that enforces stricter limits if portfolio can't be fetched.
            return 50.0
    
    def _make_approval_decision(self, validation_result: Dict[str, Any], trading_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make the final approval decision for trade execution.
        
        Args:
            validation_result: Results from plan validation
            trading_plan: The trading plan to approve or reject
            
        Returns:
            Approval decision with reasoning
        """
        # Decision factors
        validation_passed = validation_result.get("validation_passed", False)
        quality_score = validation_result.get("quality_score", 0)
        risk_level = validation_result.get("risk_level", "unknown")
        
        # Approval criteria
        approved = False
        approval_reason = ""
        
        # Reject empty trade plans (hold strategies should not be marked approved for execution)
        trades = trading_plan.get("trades") if isinstance(trading_plan, dict) else None
        if isinstance(trades, list) and len(trades) == 0:
            approval_reason = "Plan contains no trades; marked as hold."
        elif not validation_passed:
            approval_reason = f"Plan failed validation: {'; '.join(validation_result.get('validation_issues', []))}"
        elif quality_score < 0.3:
            approval_reason = f"Quality score too low: {quality_score}"
        elif risk_level == "high" and quality_score < 0.8:
            approval_reason = f"High risk with insufficient quality justification"
        else:
            approved = True
            approval_reason = f"Plan approved: Quality {quality_score:.2f}, Risk {risk_level}, Validation passed"
        
        return {
            "approved": approved,
            "approval_reason": approval_reason,
            "quality_threshold_met": quality_score >= 0.3,
            "risk_acceptable": risk_level != "high" or quality_score >= 0.8,
            "validation_clean": validation_passed,
            "decision_timestamp": datetime.now().isoformat()
        }
    
    def _execute_trades_if_approved(self, final_decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute trades if the plan was approved by the supervisor.
        
        Args:
            final_decision: The final approval decision
            
        Returns:
            Trade execution results
        """
        self.logger.info("⚡ Stage 6: Trade Execution")
        self.current_state = PipelineState.EXECUTING_TRADES
        
        approval_decision = final_decision.get("approval_decision", {})
        
        if not approval_decision.get("approved", False):
            self.logger.info(f"❌ Trades not approved: {approval_decision.get('approval_reason')}")
            result = {
                "executed": False,
                "reason": "Plan not approved by supervisor",
                "approval_reason": approval_decision.get("approval_reason"),
                "trade_results": []
            }
            # Persist for summary
            self.execution_context["trade_execution"] = result
            return result
        
        try:
            # Extract trading plan
            trading_plan = final_decision.get("trading_plan", {})
            
            self.logger.info("🚀 Executing approved trading plan")
            # Guard: approved but empty plan → treat as hold, do not execute
            if not isinstance(trading_plan, dict) or not trading_plan.get("trades"):
                self.logger.info("Plan approved but contains no trades. Treating as HOLD; no execution performed.")
                result = {
                    "executed": False,
                    "reason": "Empty approved plan (HOLD)",
                    "trade_results": [],
                    "execution_timestamp": datetime.now().isoformat()
                }
                self.execution_context["trade_execution"] = result
                return result
            
            # Execute trades using the existing trade executor
            trade_results = self.trade_executor.execute_trades(trading_plan)
            
            # Log successful trades and rejected trades
            for result in trade_results:
                if result.get("status") == "success":
                    self.performance_tracker.log_trade(result)
                elif result.get("status") == "volume_too_small":
                    # Log rejected trade for auditing with enhanced details
                    original_trade = result.get("trade", {})
                    rejection_reason = result.get("error", "Volume below minimum order size")
                    
                    # Add debugging context
                    allocation_pct = original_trade.get('allocation_percentage', 0) * 100
                    self.logger.warning(f"💸 Trade rejected: {original_trade.get('pair', 'unknown')} at {allocation_pct:.1f}% allocation - {rejection_reason}")
                    
                    self.performance_tracker.log_rejected_trade(original_trade, rejection_reason)
            
            execution_summary = {
                "executed": True,
                "total_trades": len(trade_results),
                "successful_trades": len([r for r in trade_results if r.get("status") == "success"]),
                "failed_trades": len([r for r in trade_results if r.get("status") != "success"]),
                "trade_results": trade_results,
                "execution_timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f"✅ Trade execution completed: {execution_summary['successful_trades']}/{execution_summary['total_trades']} successful")
            # Persist for summary
            self.execution_context["trade_execution"] = execution_summary
            return execution_summary
            
        except Exception as e:
            self.logger.error(f"Trade execution failed: {e}")
            result = {
                "executed": False,
                "reason": "Execution error",
                "error_message": str(e),
                "trade_results": []
            }
            self.execution_context["trade_execution"] = result
            return result
    
    def _update_performance_tracking(self, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update performance tracking and save thesis.
        
        Args:
            execution_result: Results from trade execution
            
        Returns:
            Performance tracking results
        """
        self.logger.info("📈 Stage 7: Performance Tracking")
        
        try:
            # Log current equity
            self.performance_tracker.log_equity()
            
            # Save thesis if we have one
            trader_output = self.execution_context.get("agent_outputs", {}).get("trader", {})
            trading_plan = trader_output.get("trading_plan", {})
            thesis = trading_plan.get("thesis", "")
            
            if thesis:
                self.performance_tracker.log_thesis(thesis)
            
            return {
                "equity_logged": True,
                "thesis_logged": bool(thesis),
                "tracking_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Performance tracking failed: {e}")
            return {
                "equity_logged": False,
                "thesis_logged": False,
                "error_message": str(e)
            }
    
    def _generate_pipeline_summary(self) -> Dict[str, Any]:
        """
        Generate a comprehensive summary of the pipeline execution.
        
        Returns:
            Pipeline execution summary
        """
        agent_outputs = self.execution_context.get("agent_outputs", {})
        
        return {
            "execution_id": self.execution_context.get("execution_id"),
            "start_time": self.execution_context.get("start_time"),
            "final_state": self.current_state.value,
            "agents_executed": list(agent_outputs.keys()),
            "total_errors": len(self.execution_context.get("errors", [])),
            "total_warnings": len(self.execution_context.get("warnings", [])),
            "pipeline_success": self.current_state == PipelineState.COMPLETED or self.current_state == PipelineState.EXECUTING_TRADES,
            "market_intelligence_quality": agent_outputs.get("analyst", {}).get("intelligence_quality", {}).get("quality_score"),
            "ai_decision_quality": agent_outputs.get("trader", {}).get("decision_quality", {}).get("overall_quality"),
            "trades_approved": bool(self.execution_context.get("trade_execution", {}).get("executed", False) and (self.execution_context.get("trade_execution", {}).get("successful_trades", 0) > 0)),
        }
    
    def _generate_supervisor_reasoning(self, validation_result: Dict[str, Any], approval_decision: Dict[str, Any]) -> str:
        """
        Generate supervisor reasoning for the final decision.
        
        Args:
            validation_result: Plan validation results
            approval_decision: Final approval decision
            
        Returns:
            Natural language reasoning
        """
        reasoning_parts = [
            "Supervisor Decision Analysis:",
            "",
            f"1. Plan Validation: {'PASSED' if validation_result.get('validation_passed') else 'FAILED'}",
            f"2. Quality Assessment: {validation_result.get('quality_score', 0):.2f} overall quality score",
            f"3. Risk Evaluation: {validation_result.get('risk_level', 'unknown')} risk level",
            f"4. Trade Count: {validation_result.get('trade_count', 0)} proposed trades",
            f"5. Final Decision: {'APPROVED' if approval_decision.get('approved') else 'REJECTED'}",
            "",
            f"Reasoning: {approval_decision.get('approval_reason', 'No reason provided')}"
        ]
        
        if validation_result.get("validation_issues"):
            reasoning_parts.extend([
                "",
                "Validation Issues:",
                *[f"- {issue}" for issue in validation_result.get("validation_issues", [])]
            ])
        
        if validation_result.get("validation_warnings"):
            reasoning_parts.extend([
                "",
                "Validation Warnings:",
                *[f"- {warning}" for warning in validation_result.get("validation_warnings", [])]
            ])
        
        return "\n".join(reasoning_parts)
    
    def generate_reasoning(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> str:
        """
        Generate comprehensive reasoning about the multi-agent pipeline execution.
        
        Args:
            inputs: Initial pipeline inputs
            outputs: Complete pipeline results
            
        Returns:
            Natural language explanation of the supervision process
        """
        if outputs.get("status") == "error":
            return f"Multi-agent pipeline failed: {outputs.get('error_message', 'unknown error')}. The trading cycle could not be completed."
        
        pipeline_summary = outputs.get("pipeline_result", {}).get("pipeline_summary", {})
        final_decision = outputs.get("pipeline_result", {}).get("final_decision", {})
        
        reasoning = f"""
        Multi-Agent Pipeline Supervision Summary:
        
        1. Orchestration: Successfully coordinated {len(pipeline_summary.get('agents_executed', []))} specialized AI agents through complete trading pipeline
        2. Intelligence Gathering: Market analysis quality: {pipeline_summary.get('market_intelligence_quality', 'unknown')}
        3. Decision Quality: AI trading decision quality: {pipeline_summary.get('ai_decision_quality', 0)*100:.0f}%
        4. Risk Management: Implemented comprehensive validation with {len(final_decision.get('validation_result', {}).get('validation_warnings', []))} warnings and {len(final_decision.get('validation_result', {}).get('validation_issues', []))} issues
        5. Final Decision: {'APPROVED' if pipeline_summary.get('trades_approved') else 'REJECTED'} trading plan based on quality and risk thresholds
        6. Context Sharing: Successfully maintained shared context across all agents preventing fragmentation issues
        7. Error Handling: {pipeline_summary.get('total_errors', 0)} errors and {pipeline_summary.get('total_warnings', 0)} warnings handled gracefully
        
        Pipeline execution {'completed successfully' if pipeline_summary.get('pipeline_success') else 'encountered issues'} with full cognitive transparency and audit trail maintained.
        """
        
        return reasoning.strip()
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current execution context.
        
        Returns:
            Current execution context and state
        """
        return {
            "current_state": self.current_state.value,
            "execution_context": self.execution_context,
            "agents_available": ["CoinGecko-AI", "Analyst-AI", "Strategist-AI", "Trader-AI"],
            "pipeline_ready": True
        }