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

from bot.kraken_api import KrakenAPI
from bot.trade_executor import TradeExecutor
from bot.performance_tracker import PerformanceTracker

logger = logging.getLogger(__name__)

class PipelineState(Enum):
    """Enumeration of possible pipeline states."""
    IDLE = "idle"
    RUNNING_COINGECKO = "running_coingecko"
    RUNNING_ANALYST = "running_analyst"
    RUNNING_STRATEGIST = "running_strategist"
    RUNNING_TRADER = "running_trader"
    REVIEWING_PLAN = "reviewing_plan"
    EXECUTING_TRADES = "executing_trades"
    COMPLETED = "completed"
    FAILED = "failed"

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
    
    def __init__(self, kraken_api: KrakenAPI, logs_dir: str = "logs"):
        """
        Initialize the Supervisor Agent.
        
        Args:
            kraken_api: Kraken API instance for trading operations
            logs_dir: Directory for saving agent transcripts
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
        self.coingecko = CoinGeckoAgent(logs_dir, session_dir)
        self.analyst = AnalystAgent(logs_dir, session_dir)
        self.strategist = StrategistAgent(kraken_api, logs_dir, session_dir)
        self.trader = TraderAgent(logs_dir, session_dir)
        
        # Pipeline state tracking
        self.current_state = PipelineState.IDLE
        self.execution_context = {}
        
        self.logger.info(f"Supervisor-AI initialized with unified session: {session_dir}")
        self.logger.info("Complete agent team initialized with shared session directory")
    
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
            "warnings": []
        }
        
        try:
            # Execute the complete pipeline
            pipeline_result = self._execute_pipeline(inputs)
            
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
    
    def _execute_pipeline(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the complete multi-agent pipeline with state management.
        
        Args:
            inputs: Initial inputs for the pipeline
            
        Returns:
            Complete pipeline execution results
        """
        # Step 1: CoinGecko Market Data Gathering
        coingecko_result = self._run_coingecko_stage(inputs)
        
        # Step 2: Market Intelligence Gathering (with CoinGecko data)
        analyst_result = self._run_analyst_stage(coingecko_result, inputs)
        
        # Step 3: Strategic Prompt Construction (with CoinGecko data)
        strategist_result = self._run_strategist_stage(analyst_result, coingecko_result, inputs)
        
        # Step 4: AI Trading Decision Generation
        trader_result = self._run_trader_stage(strategist_result, inputs)
        
        # Step 5: Final Review and Decision
        final_decision = self._review_trading_plan(trader_result)
        
        # Step 6: Trade Execution (if approved)
        execution_result = self._execute_trades_if_approved(final_decision)
        
        # Step 7: Performance Tracking
        tracking_result = self._update_performance_tracking(execution_result)
        
        return {
            "coingecko_result": coingecko_result,
            "analyst_result": analyst_result,
            "strategist_result": strategist_result,
            "trader_result": trader_result,
            "final_decision": final_decision,
            "execution_result": execution_result,
            "tracking_result": tracking_result,
            "pipeline_summary": self._generate_pipeline_summary()
        }
    
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
                self.execution_context["errors"].append(f"CoinGecko-AI failed: {coingecko_result.get('error_message')}")
                raise Exception(f"Market data gathering failed: {coingecko_result.get('error_message')}")
            
            self.logger.info("✅ CoinGecko-AI completed successfully")
            return coingecko_result
            
        except Exception as e:
            self.logger.error(f"CoinGecko stage failed: {e}")
            self.execution_context["errors"].append(f"CoinGecko stage failure: {str(e)}")
            raise
    
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
                self.execution_context["errors"].append(f"Analyst-AI failed: {analyst_result.get('error_message')}")
                raise Exception(f"Market intelligence gathering failed: {analyst_result.get('error_message')}")
            
            self.logger.info("✅ Analyst-AI completed successfully")
            return analyst_result
            
        except Exception as e:
            self.logger.error(f"Analyst stage failed: {e}")
            self.execution_context["errors"].append(f"Analyst stage failure: {str(e)}")
            raise
    
    def _run_strategist_stage(self, analyst_result: Dict[str, Any], coingecko_result: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the Strategist-AI stage of the pipeline.
        
        Args:
            analyst_result: Results from the Analyst-AI
            coingecko_result: Results from the CoinGecko-AI
            inputs: Original pipeline inputs
            
        Returns:
            Strategist execution results
        """
        self.logger.info("🧠 Stage 3: Running Strategic Prompt Construction")
        self.current_state = PipelineState.RUNNING_STRATEGIST
        
        try:
            # Prepare strategist inputs with shared context
            strategist_inputs = {
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
            self.logger.error(f"Strategist stage failed: {e}")
            self.execution_context["errors"].append(f"Strategist stage failure: {str(e)}")
            raise
    
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
            self.logger.error(f"Trader stage failed: {e}")
            self.execution_context["errors"].append(f"Trader stage failure: {str(e)}")
            raise
    
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
        if not trading_plan.get("trades") or not isinstance(trading_plan.get("trades"), list):
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
        
        # Check 5: Thesis quality
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
        
        if not validation_passed:
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
            return {
                "executed": False,
                "reason": "Plan not approved by supervisor",
                "approval_reason": approval_decision.get("approval_reason"),
                "trade_results": []
            }
        
        try:
            # Extract trading plan
            trading_plan = final_decision.get("trading_plan", {})
            
            self.logger.info("🚀 Executing approved trading plan")
            
            # Execute trades using the existing trade executor
            trade_results = self.trade_executor.execute_trades(trading_plan)
            
            # Log successful trades
            for result in trade_results:
                if result.get("status") == "success":
                    self.performance_tracker.log_trade(result)
            
            execution_summary = {
                "executed": True,
                "total_trades": len(trade_results),
                "successful_trades": len([r for r in trade_results if r.get("status") == "success"]),
                "failed_trades": len([r for r in trade_results if r.get("status") != "success"]),
                "trade_results": trade_results,
                "execution_timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f"✅ Trade execution completed: {execution_summary['successful_trades']}/{execution_summary['total_trades']} successful")
            return execution_summary
            
        except Exception as e:
            self.logger.error(f"Trade execution failed: {e}")
            return {
                "executed": False,
                "reason": "Execution error",
                "error_message": str(e),
                "trade_results": []
            }
    
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
            "trades_approved": self.execution_context.get("final_review", {}).get("approval_decision", {}).get("approved", False)
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