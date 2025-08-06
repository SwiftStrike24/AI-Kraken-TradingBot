"""
Base Agent Class

Provides common functionality for all trading bot agents including
logging, error handling, and standardized communication protocols.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from bot.logger import get_logger

# Set up logging
# logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """
    Abstract base class for all trading bot agents.
    
    Provides standardized logging, error handling, and communication patterns
    that ensure all agents operate with shared context and transparent reasoning.
    """
    
    def __init__(self, agent_name: str, logs_dir: str = "logs", session_dir: Optional[str] = None):
        """
        Initialize the base agent.
        
        Args:
            agent_name: Human-readable name for this agent (e.g., "Analyst-AI")
            logs_dir: Directory where agent transcripts will be saved
            session_dir: Optional specific session directory path. If None, creates based on current time.
        """
        self.agent_name = agent_name
        self.logs_dir = logs_dir
        self.transcript_dir = os.path.join(logs_dir, "agent_transcripts")
        
        # Ensure transcript directory exists
        os.makedirs(self.transcript_dir, exist_ok=True)
        
        # Use provided session directory or create one based on current time
        if session_dir:
            self.session_transcript_dir = session_dir
            os.makedirs(self.session_transcript_dir, exist_ok=True)
        else:
            # Create organized transcript directory structure: YYYY-MM-DD/HH-MM-SS/
            now = datetime.now()
            today = now.strftime('%Y-%m-%d')
            time_folder = now.strftime('%H-%M-%S')
            
            self.daily_transcript_dir = os.path.join(self.transcript_dir, today)
            self.session_transcript_dir = os.path.join(self.daily_transcript_dir, time_folder)
            os.makedirs(self.session_transcript_dir, exist_ok=True)
        
        self.logger = get_logger(f"agents.{agent_name.lower().replace('-', '_')}")
    
    def log_thoughts(self, inputs: Dict[str, Any], reasoning: str, outputs: Dict[str, Any]) -> str:
        """
        Log the agent's cognitive process to a timestamped Markdown transcript file.
        
        This provides full transparency into how each agent processes information
        and makes decisions, enabling debugging and performance analysis.
        
        Args:
            inputs: The exact data the agent received
            reasoning: Natural language explanation of the agent's thought process
            outputs: The final structured output the agent produced
            
        Returns:
            Path to the saved transcript file
        """
        timestamp = datetime.now()
        iso_timestamp = timestamp.isoformat()
        file_timestamp = timestamp.strftime('%H-%M-%S')
        
        # Create readable Markdown transcript
        markdown_content = self._create_markdown_transcript(
            timestamp, inputs, reasoning, outputs, "success"
        )
        
        # Save thoughts transcript as Markdown
        thoughts_file = f"{self.agent_name.lower().replace('-', '_')}_thoughts_{file_timestamp}.md"
        thoughts_path = os.path.join(self.session_transcript_dir, thoughts_file)
        
        try:
            with open(thoughts_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            self.logger.info(f"Cognitive transcript saved: {thoughts_path}")
            return thoughts_path
            
        except Exception as e:
            self.logger.error(f"Failed to save cognitive transcript: {e}")
            return ""
    
    def log_error(self, inputs: Dict[str, Any], error: Exception) -> str:
        """
        Log an agent execution error with full context in Markdown format.
        
        Args:
            inputs: The inputs that led to the error
            error: The exception that occurred
            
        Returns:
            Path to the saved error transcript
        """
        timestamp = datetime.now()
        file_timestamp = timestamp.strftime('%H-%M-%S')
        
        # Create error reasoning
        error_reasoning = f"❌ **EXECUTION FAILED**\n\n**Error Type:** {type(error).__name__}\n\n**Error Message:** {str(error)}\n\nThe agent failed to complete its execution due to the above error. All input context and error details are preserved below for debugging."
        
        # Create error outputs
        error_outputs = {
            "status": "error",
            "error_type": type(error).__name__,
            "error_message": str(error)
        }
        
        # Create readable Markdown transcript
        markdown_content = self._create_markdown_transcript(
            timestamp, inputs, error_reasoning, error_outputs, "error"
        )
        
        # Save error transcript as Markdown
        error_file = f"{self.agent_name.lower().replace('-', '_')}_error_{file_timestamp}.md"
        error_path = os.path.join(self.session_transcript_dir, error_file)
        
        try:
            with open(error_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            self.logger.error(f"Error transcript saved: {error_path}")
            return error_path
            
        except Exception as e:
            self.logger.error(f"Failed to save error transcript: {e}")
            return ""
    
    def save_output(self, output_data: Dict[str, Any]) -> str:
        """
        Save the agent's final output to a dedicated Markdown file for inter-agent communication.
        
        Args:
            output_data: The structured output data to save
            
        Returns:
            Path to the saved output file
        """
        timestamp = datetime.now().strftime('%H-%M-%S')
        output_file = f"{self.agent_name.lower().replace('-', '_')}_output_{timestamp}.md"
        output_path = os.path.join(self.session_transcript_dir, output_file)
        
        try:
            # Create readable Markdown output
            markdown_content = f"# {self.agent_name} - Final Output\n\n"
            markdown_content += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            markdown_content += f"**Status:** {output_data.get('status', 'unknown')}\n\n"
            
            # Format output data in a readable way
            markdown_content += "## 📊 Output Data\n\n"
            markdown_content += self._format_dict_as_markdown(output_data, level=3)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            self.logger.info(f"Agent output saved: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Failed to save agent output: {e}")
            return ""
    
    @abstractmethod
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent's core function.
        
        This method must be implemented by each specific agent class.
        It should perform the agent's specialized task and return structured output.
        
        Args:
            inputs: Structured input data from the supervisor or previous agent
            
        Returns:
            Structured output data for the next agent in the pipeline
        """
        pass
    
    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent with full logging and error handling.
        
        This is the main entry point that the supervisor uses to run any agent.
        It ensures all agents follow the same execution pattern.
        
        Args:
            inputs: Input data for the agent
            
        Returns:
            The agent's output, or an error structure if execution failed
        """
        self.logger.info(f"Starting execution: {self.agent_name}")
        
        try:
            # Execute the agent's core function
            outputs = self.execute(inputs)
            
            # Generate reasoning explanation (can be overridden by specific agents)
            reasoning = self.generate_reasoning(inputs, outputs)
            
            # Log the complete cognitive process
            self.log_thoughts(inputs, reasoning, outputs)
            
            # Save output for inter-agent communication
            self.save_output(outputs)
            
            self.logger.info(f"Execution completed successfully: {self.agent_name}")
            return outputs
            
        except Exception as e:
            self.logger.error(f"Execution failed: {self.agent_name} - {e}")
            
            # Log the error with full context
            self.log_error(inputs, e)
            
            # Return error structure
            return {
                "status": "error",
                "agent": self.agent_name,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "inputs": inputs
            }
    
    def generate_reasoning(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> str:
        """
        Generate a natural language explanation of the agent's reasoning.
        
        This default implementation provides basic reasoning.
        Specific agents can override this for more detailed explanations.
        
        Args:
            inputs: The input data the agent processed
            outputs: The output data the agent produced
            
        Returns:
            Natural language explanation of the reasoning process
        """
        return f"{self.agent_name} processed {len(inputs)} input fields and generated {len(outputs)} output fields. Execution completed according to standard procedures."
    
    def _create_markdown_transcript(self, timestamp: datetime, inputs: Dict[str, Any], 
                                  reasoning: str, outputs: Dict[str, Any], status: str) -> str:
        """
        Create a comprehensive Markdown transcript of the agent's cognitive process.
        
        Args:
            timestamp: Execution timestamp
            inputs: Input data
            reasoning: Agent's reasoning process
            outputs: Output data
            status: Execution status
            
        Returns:
            Formatted Markdown content
        """
        # Create the main transcript structure
        markdown_content = f"# {self.agent_name} - Cognitive Transcript\n\n"
        
        # Header with metadata
        markdown_content += f"**🕐 Timestamp:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        markdown_content += f"**📊 Status:** {'✅ Success' if status == 'success' else '❌ Error'}\n\n"
        markdown_content += f"**🆔 Execution ID:** {self.agent_name.lower().replace('-', '_')}_{timestamp.strftime('%H-%M-%S')}\n\n"
        
        markdown_content += "---\n\n"
        
        # Inputs section
        markdown_content += "## 📥 Input Data\n\n"
        if inputs:
            markdown_content += self._format_dict_as_markdown(inputs, level=3)
        else:
            markdown_content += "*No input data provided*\n\n"
        
        # Reasoning section
        markdown_content += "## 🧠 Cognitive Process & Reasoning\n\n"
        markdown_content += f"{reasoning}\n\n"
        
        # Outputs section
        markdown_content += "## 📤 Output Data\n\n"
        if outputs:
            markdown_content += self._format_dict_as_markdown(outputs, level=3)
        else:
            markdown_content += "*No output data generated*\n\n"
        
        # Footer
        markdown_content += "---\n\n"
        markdown_content += f"*Generated by {self.agent_name} on {timestamp.strftime('%Y-%m-%d %H:%M:%S')}*\n"
        
        return markdown_content
    
    def _format_dict_as_markdown(self, data: Dict[str, Any], level: int = 1) -> str:
        """
        Format a dictionary as readable Markdown.
        
        Args:
            data: Dictionary to format
            level: Header level for nested structures
            
        Returns:
            Formatted Markdown string
        """
        markdown = ""
        
        for key, value in data.items():
            # Create header
            header_prefix = "#" * level
            formatted_key = key.replace('_', ' ').title()
            markdown += f"{header_prefix} {formatted_key}\n\n"
            
            # Format value based on type
            if isinstance(value, dict):
                if value:
                    markdown += self._format_dict_as_markdown(value, level + 1)
                else:
                    markdown += "*Empty dictionary*\n\n"
            elif isinstance(value, list):
                if value:
                    markdown += self._format_list_as_markdown(value)
                else:
                    markdown += "*Empty list*\n\n"
            elif isinstance(value, str):
                if len(value) > 100:
                    # For long strings, format as code block
                    markdown += f"```\n{value}\n```\n\n"
                else:
                    markdown += f"{value}\n\n"
            else:
                markdown += f"`{value}`\n\n"
        
        return markdown
    
    def _format_list_as_markdown(self, data: list) -> str:
        """
        Format a list as readable Markdown.
        
        Args:
            data: List to format
            
        Returns:
            Formatted Markdown string
        """
        markdown = ""
        
        for i, item in enumerate(data):
            if isinstance(item, dict):
                markdown += f"**Item {i+1}:**\n\n"
                markdown += self._format_dict_as_markdown(item, level=4)
            elif isinstance(item, str):
                markdown += f"- {item}\n"
            else:
                markdown += f"- `{item}`\n"
        
        markdown += "\n"
        return markdown