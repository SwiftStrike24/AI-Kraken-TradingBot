"""
Trader Agent (AI Execution Specialist)

This agent specializes in executing AI calls to OpenAI and parsing the resulting
trading decisions. It ensures the AI receives optimal prompts and returns
well-structured, actionable trading plans.

This replaces the AI execution logic from decision_engine.py with a more focused,
cognitive approach that provides transparent reasoning about AI decision quality.
"""

import json
import logging
from typing import Dict, Any
from datetime import datetime

from openai import OpenAI, APIError

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

class TraderAgent(BaseAgent):
    """
    The Trader-AI specializes in AI execution and decision parsing.
    
    This agent:
    1. Receives optimized prompt payloads from the Strategist-AI
    2. Executes calls to OpenAI's GPT-4o model
    3. Parses and validates the AI's trading decisions
    4. Provides structured trade plans to the execution system
    """
    
    def __init__(self, logs_dir: str = "logs", session_dir: str = None):
        """
        Initialize the Trader Agent.
        
        Args:
            logs_dir: Directory for saving agent transcripts
            session_dir: Optional session directory for unified transcript storage
        """
        super().__init__("Trader-AI", logs_dir, session_dir)
        
        # Initialize OpenAI client
        try:
            self.openai_client = OpenAI()  # API key loaded from environment
            self.logger.info("OpenAI client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {e}")
            raise
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute AI trading decision generation.
        
        Args:
            inputs: Contains prompt payload from Strategist-AI and supervisor directives
            
        Returns:
            Structured trading plan with AI decisions and reasoning
        """
        self.logger.info("Beginning AI trading decision generation...")
        
        try:
            # Extract the prompt payload
            prompt_payload = inputs.get('prompt_payload', {})
            supervisor_directives = inputs.get('supervisor_directives', {})
            
            # Validate prompt payload
            if not prompt_payload or not prompt_payload.get('prompt_text'):
                raise ValueError("Invalid or missing prompt payload from Strategist-AI")
            
            # Execute the AI call
            ai_response = self._execute_ai_call(prompt_payload, supervisor_directives)
            
            # Parse and validate the response
            parsed_decision = self._parse_ai_response(ai_response)
            
            # Assess decision quality
            decision_quality = self._assess_decision_quality(parsed_decision, prompt_payload)
            
            self.logger.info("AI trading decision generation completed successfully")
            
            return {
                "status": "success",
                "agent": "Trader-AI",
                "timestamp": datetime.now().isoformat(),
                "trading_plan": parsed_decision,
                "ai_response_raw": ai_response,
                "decision_quality": decision_quality,
                "prompt_summary": self._summarize_prompt(prompt_payload),
                "execution_metrics": self._capture_execution_metrics(prompt_payload, ai_response)
            }
            
        except Exception as e:
            self.logger.error(f"AI trading decision generation failed: {e}")
            raise
    
    def _execute_ai_call(self, prompt_payload: Dict[str, Any], directives: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the call to OpenAI's API with the constructed prompt.
        
        Args:
            prompt_payload: Complete prompt from Strategist-AI
            directives: Any special execution directives from Supervisor-AI
            
        Returns:
            Raw response from OpenAI API
        """
        prompt_text = prompt_payload.get('prompt_text', '')
        
        # Configure model parameters (can be overridden by supervisor directives)
        model = directives.get('model', 'gpt-4o')
        temperature = directives.get('temperature', 0.1)  # Low temperature for consistent trading decisions
        max_tokens = directives.get('max_tokens', 1000)
        
        try:
            self.logger.info(f"Calling OpenAI API with model: {model}")
            self.logger.debug(f"Prompt length: {len(prompt_text)} characters")
            
            # Make the API call
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt_text}],
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Extract response content
            response_content = response.choices[0].message.content
            
            self.logger.info("OpenAI API call completed successfully")
            self.logger.debug(f"Response length: {len(response_content)} characters")
            
            return {
                "content": response_content,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "finish_reason": response.choices[0].finish_reason
            }
            
        except APIError as e:
            self.logger.error(f"OpenAI API error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during AI call: {e}")
            raise
    
    def _parse_ai_response(self, ai_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and validate the AI's JSON response.
        
        Args:
            ai_response: Raw response from OpenAI API
            
        Returns:
            Parsed and validated trading decision
        """
        response_content = ai_response.get('content', '')
        
        try:
            # Parse JSON response
            decision = json.loads(response_content)
            
            # Validate required fields
            if 'trades' not in decision or 'thesis' not in decision:
                raise ValueError("AI response missing required 'trades' or 'thesis' fields")
            
            # Validate trades format
            trades = decision.get('trades', [])
            if not isinstance(trades, list):
                raise ValueError("'trades' field must be a list")
            
            # Validate each trade
            validated_trades = []
            for i, trade in enumerate(trades):
                validated_trade = self._validate_trade_format(trade, i)
                validated_trades.append(validated_trade)
            
            # Validate thesis
            thesis = decision.get('thesis', '')
            if not isinstance(thesis, str) or not thesis.strip():
                raise ValueError("'thesis' field must be a non-empty string")
            
            return {
                "trades": validated_trades,
                "thesis": thesis.strip(),
                "raw_decision": decision,
                "validation_status": "passed",
                "trade_count": len(validated_trades)
            }
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode JSON from AI response: {e}")
            raise ValueError(f"Invalid JSON response from AI: {e}")
        except ValueError as e:
            self.logger.error(f"Invalid AI response format: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error parsing AI response: {e}")
            raise
    
    def _validate_trade_format(self, trade: Dict[str, Any], index: int) -> Dict[str, Any]:
        """
        Validate and normalize a single trade object.
        
        Args:
            trade: Individual trade from AI response
            index: Trade index for error reporting
            
        Returns:
            Validated and normalized trade object
        """
        # Required fields
        required_fields = ['pair', 'action', 'volume']
        for field in required_fields:
            if field not in trade:
                raise ValueError(f"Trade {index}: missing required field '{field}'")
        
        # Validate pair format
        pair = str(trade['pair']).upper().strip()
        if not pair or '/' not in pair:
            raise ValueError(f"Trade {index}: invalid pair format '{trade['pair']}'")
        
        # Validate action
        action = str(trade['action']).lower().strip()
        if action not in ['buy', 'sell']:
            raise ValueError(f"Trade {index}: action must be 'buy' or 'sell', got '{trade['action']}'")
        
        # Validate volume
        try:
            volume = float(trade['volume'])
            if volume <= 0:
                raise ValueError(f"Trade {index}: volume must be positive, got {volume}")
        except (ValueError, TypeError):
            raise ValueError(f"Trade {index}: invalid volume format '{trade['volume']}'")
        
        return {
            "pair": pair,
            "action": action,
            "volume": volume,
            "validated": True
        }
    
    def _assess_decision_quality(self, parsed_decision: Dict[str, Any], prompt_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess the quality and validity of the AI's trading decision.
        
        Args:
            parsed_decision: Validated trading decision
            prompt_payload: Original prompt that generated this decision
            
        Returns:
            Quality assessment metrics
        """
        trades = parsed_decision.get('trades', [])
        thesis = parsed_decision.get('thesis', '')
        
        # Calculate quality scores
        trade_count = len(trades)
        thesis_length = len(thesis.split())
        
        # Assess decision complexity
        if trade_count == 0:
            decision_type = "hold"
            complexity = "simple"
        elif trade_count <= 2:
            decision_type = "focused"
            complexity = "moderate"
        else:
            decision_type = "complex"
            complexity = "high"
        
        # Assess thesis quality
        if thesis_length < 20:
            thesis_quality = "brief"
        elif thesis_length < 50:
            thesis_quality = "adequate"
        else:
            thesis_quality = "detailed"
        
        # Overall quality score
        quality_factors = []
        
        # Factor 1: Appropriate response to market conditions
        quality_factors.append(0.8 if trade_count > 0 else 0.6)  # Bias toward action if market intelligence provided
        
        # Factor 2: Thesis quality
        quality_factors.append(0.9 if thesis_quality == "detailed" else 0.7 if thesis_quality == "adequate" else 0.5)
        
        # Factor 3: Decision structure
        quality_factors.append(1.0 if parsed_decision.get('validation_status') == 'passed' else 0.3)
        
        overall_quality = sum(quality_factors) / len(quality_factors)
        
        return {
            "overall_quality": round(overall_quality, 2),
            "quality_grade": "excellent" if overall_quality > 0.85 else "good" if overall_quality > 0.7 else "fair" if overall_quality > 0.5 else "poor",
            "decision_type": decision_type,
            "complexity": complexity,
            "trade_count": trade_count,
            "thesis_quality": thesis_quality,
            "thesis_word_count": thesis_length,
            "validation_passed": parsed_decision.get('validation_status') == 'passed',
            "risk_assessment": self._assess_risk_level(trades)
        }
    
    def _assess_risk_level(self, trades: list) -> str:
        """
        Assess the risk level of the proposed trades.
        
        Args:
            trades: List of validated trades
            
        Returns:
            Risk level assessment
        """
        if not trades:
            return "none"
        
        # Simple risk assessment based on number and type of trades
        trade_count = len(trades)
        
        # Check for high-volume trades (simplified - could be enhanced with actual portfolio analysis)
        high_volume_trades = sum(1 for trade in trades if trade.get('volume', 0) > 0.1)
        
        if trade_count <= 1 and high_volume_trades == 0:
            return "low"
        elif trade_count <= 2 and high_volume_trades <= 1:
            return "moderate"
        else:
            return "high"
    
    def _summarize_prompt(self, prompt_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a summary of the prompt that was sent to the AI.
        
        Args:
            prompt_payload: Original prompt payload
            
        Returns:
            Prompt summary for logging
        """
        return {
            "estimated_tokens": prompt_payload.get('estimated_tokens', 0),
            "research_included": 'research_summary' in prompt_payload,
            "portfolio_included": 'portfolio_summary' in prompt_payload,
            "strategic_focus": prompt_payload.get('strategic_focus', 'unknown'),
            "construction_time": prompt_payload.get('construction_timestamp', '')
        }
    
    def _capture_execution_metrics(self, prompt_payload: Dict[str, Any], ai_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Capture metrics about the AI execution for performance analysis.
        
        Args:
            prompt_payload: Original prompt
            ai_response: AI response data
            
        Returns:
            Execution metrics
        """
        usage = ai_response.get('usage', {})
        
        return {
            "model_used": ai_response.get('model', 'unknown'),
            "prompt_tokens": usage.get('prompt_tokens', 0),
            "completion_tokens": usage.get('completion_tokens', 0),
            "total_tokens": usage.get('total_tokens', 0),
            "finish_reason": ai_response.get('finish_reason', 'unknown'),
            "estimated_cost_usd": self._estimate_api_cost(usage),
            "response_length": len(ai_response.get('content', '')),
            "execution_timestamp": datetime.now().isoformat()
        }
    
    def _estimate_api_cost(self, usage: Dict[str, Any]) -> float:
        """
        Estimate the cost of the API call based on token usage.
        
        Args:
            usage: Token usage data from OpenAI
            
        Returns:
            Estimated cost in USD
        """
        # GPT-4o pricing as of August 2025 (approximate)
        prompt_cost_per_token = 0.005 / 1000  # $0.005 per 1K prompt tokens
        completion_cost_per_token = 0.015 / 1000  # $0.015 per 1K completion tokens
        
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        
        estimated_cost = (prompt_tokens * prompt_cost_per_token) + (completion_tokens * completion_cost_per_token)
        
        return round(estimated_cost, 4)
    
    def generate_reasoning(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> str:
        """
        Generate detailed reasoning about the AI execution and decision quality.
        
        Args:
            inputs: Input prompt payload
            outputs: Generated trading plan
            
        Returns:
            Natural language explanation of the AI execution process
        """
        if outputs.get("status") == "error":
            return f"AI trading decision generation failed: {outputs.get('error_message', 'unknown error')}. No trading plan could be produced."
        
        decision_quality = outputs.get("decision_quality", {})
        execution_metrics = outputs.get("execution_metrics", {})
        trading_plan = outputs.get("trading_plan", {})
        
        reasoning = f"""
        AI Trading Decision Analysis:
        
        1. AI Execution: Successfully called {execution_metrics.get('model_used', 'unknown')} model using {execution_metrics.get('total_tokens', 0)} tokens (cost: ${execution_metrics.get('estimated_cost_usd', 0):.4f})
        2. Decision Quality: {decision_quality.get('quality_grade', 'unknown')} grade with {decision_quality.get('overall_quality', 0)*100:.0f}% quality score
        3. Trading Plan: {decision_quality.get('decision_type', 'unknown')} strategy with {decision_quality.get('trade_count', 0)} proposed trades ({decision_quality.get('complexity', 'unknown')} complexity)
        4. Risk Assessment: {decision_quality.get('risk_assessment', 'unknown')} risk level based on trade analysis
        5. Strategic Reasoning: {decision_quality.get('thesis_quality', 'unknown')} thesis with {decision_quality.get('thesis_word_count', 0)} words of strategic explanation
        6. Validation: All trades passed format validation and are ready for execution review
        
        The AI produced a {decision_quality.get('quality_grade', 'unknown')} quality trading decision based on comprehensive market intelligence and portfolio context. The decision demonstrates {decision_quality.get('complexity', 'unknown')} strategic thinking and is ready for supervisor review.
        """
        
        return reasoning.strip()