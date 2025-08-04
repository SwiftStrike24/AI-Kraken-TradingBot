import os
import logging
from typing import Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PromptEngineError(Exception):
    """Custom exception for errors within the Prompt Engine."""
    pass

class PromptEngine:
    """
    Advanced prompt engineering module for building structured, context-rich prompts
    for the ChatGPT trading bot. Handles template loading, context injection,
    intelligent truncation, and future-proofing for advanced features.
    """
    
    def __init__(self, template_path: str = "bot/prompt_template.md", max_tokens: int = 3000):
        """
        Initialize the PromptEngine.
        
        Args:
            template_path: Path to the prompt template file
            max_tokens: Maximum tokens to allow for research report (for truncation)
        """
        self.template_path = template_path
        self.max_tokens = max_tokens
        self._template = self._load_template()
        
        # Create logs directory for prompt logging
        self.prompt_logs_dir = "logs/prompts"
        os.makedirs(self.prompt_logs_dir, exist_ok=True)
        
    def _load_template(self) -> str:
        """
        Load the prompt template from file.
        
        Returns:
            The template string with placeholder variables
            
        Raises:
            PromptEngineError: If template file cannot be loaded
        """
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            logger.info(f"Successfully loaded prompt template from {self.template_path}")
            return template
        except FileNotFoundError:
            raise PromptEngineError(f"Prompt template not found at {self.template_path}")
        except Exception as e:
            raise PromptEngineError(f"Failed to load prompt template: {e}")
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Rough estimation of token count for text.
        Uses approximation of ~4 characters per token for English text.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        return len(text) // 4
    
    def _truncate_text(self, text: str) -> str:
        """
        Intelligently truncate research report to fit within token limits.
        Preserves header and most recent content while removing middle sections.
        
        Args:
            text: Research report text to truncate
            
        Returns:
            Truncated text that fits within max_tokens
        """
        if not text or not text.strip():
            return text
            
        estimated_tokens = self._estimate_tokens(text)
        
        if estimated_tokens <= self.max_tokens:
            return text
            
        logger.warning(f"Research report is ~{estimated_tokens} tokens, truncating to {self.max_tokens}")
        
        # Split by lines and preserve structure
        lines = text.split('\n')
        
        # Always keep the header (first 10 lines)
        header_lines = lines[:10]
        remaining_lines = lines[10:]
        
        # Calculate remaining budget after header
        header_text = '\n'.join(header_lines)
        header_tokens = self._estimate_tokens(header_text)
        remaining_budget = self.max_tokens - header_tokens - 100  # Buffer for truncation notice
        
        if remaining_budget <= 0:
            # Header itself is too long, just return first few lines
            truncated_header = '\n'.join(lines[:5])
            return f"{truncated_header}\n\n[Content truncated due to length]"
        
        # Take recent lines that fit in remaining budget
        selected_lines = []
        current_tokens = 0
        
        # Work backwards from the end to prioritize recent content
        for line in reversed(remaining_lines):
            line_tokens = self._estimate_tokens(line)
            if current_tokens + line_tokens <= remaining_budget:
                selected_lines.insert(0, line)
                current_tokens += line_tokens
            else:
                break
        
        # Combine header + selected recent content + truncation notice
        result_lines = header_lines
        if selected_lines:
            result_lines.extend(["", "[... middle content truncated ...]", ""])
            result_lines.extend(selected_lines)
        else:
            result_lines.extend(["", "[Content truncated due to length]"])
            
        return '\n'.join(result_lines)
    
    def _generate_performance_review(self) -> str:
        """
        Generate performance feedback summary for the thesis feedback loop.
        
        V1 Implementation: Returns placeholder text
        V2 Future: Will analyze trades.csv and equity.csv for actual performance data
        
        Returns:
            Performance review text for prompt injection
        """
        # V1: Simple placeholder implementation
        return "No performance data available for review (feature pending)."
        
        # V2 Future implementation would:
        # 1. Read logs/trades.csv and logs/equity.csv
        # 2. Calculate recent thesis accuracy and trade performance
        # 3. Return structured feedback like:
        #    "Last thesis achieved +3.2% vs BTC. SOL position was profitable (+5.1%). 
        #     Strategy shows positive momentum over last 7 days."
    
    def build_prompt(self, portfolio_context: str, research_report: str, last_thesis: str, coingecko_data: str = "") -> str:
        """
        Build the complete prompt by injecting context into the template.
        
        Args:
            portfolio_context: Current portfolio state and cash balance
            research_report: Market intelligence report from ResearchAgent
            last_thesis: Previous investment thesis
            coingecko_data: Real-time market data from CoinGecko
            
        Returns:
            Complete prompt string ready for OpenAI API
            
        Raises:
            PromptEngineError: If prompt building fails
        """
        try:
            # Truncate research report if needed
            truncated_research = self._truncate_text(research_report)
            
            # Generate performance review
            performance_review = self._generate_performance_review()
            
            # Inject all context into template
            prompt = self._template.format(
                portfolio_context=portfolio_context,
                research_report=truncated_research,
                last_thesis=last_thesis,
                coingecko_data=coingecko_data,
                performance_review=performance_review
            )
            
            # Log the final prompt for debugging
            self._log_prompt(prompt)
            
            logger.info("Successfully built complete prompt with all context")
            return prompt
            
        except KeyError as e:
            raise PromptEngineError(f"Missing template variable: {e}")
        except Exception as e:
            raise PromptEngineError(f"Failed to build prompt: {e}")
    
    def _log_prompt(self, prompt: str):
        """
        Log the complete prompt to file for debugging and audit purposes.
        
        Args:
            prompt: The complete prompt to log
        """
        try:
            from datetime import datetime
            timestamp = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
            log_filename = f"prompt_{timestamp}.txt"
            log_path = os.path.join(self.prompt_logs_dir, log_filename)
            
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(f"=== PROMPT LOG ===\n")
                f.write(f"Timestamp: {datetime.utcnow().isoformat()}\n")
                f.write(f"Template: {self.template_path}\n")
                f.write(f"Max Tokens: {self.max_tokens}\n")
                f.write(f"Estimated Tokens: {self._estimate_tokens(prompt)}\n")
                f.write(f"==================\n\n")
                f.write(prompt)
            
            logger.debug(f"Logged prompt to {log_path}")
            
        except Exception as e:
            logger.warning(f"Failed to log prompt: {e}")
    
    def build_openai_request(self, portfolio_context: str, research_report: str, 
                           last_thesis: str, coingecko_data: str = "", model: str = "gpt-4o") -> dict:
        """
        Build complete OpenAI API request object (future-proofing for tool use).
        
        V1 Implementation: Returns basic chat completion request
        V2 Future: Will support tools and function calling
        
        Args:
            portfolio_context: Current portfolio state
            research_report: Market intelligence report  
            last_thesis: Previous investment thesis
            coingecko_data: Real-time market data from CoinGecko
            model: OpenAI model to use
            
        Returns:
            Complete request object for OpenAI API
        """
        prompt = self.build_prompt(portfolio_context, research_report, last_thesis, coingecko_data)
        
        # V1: Basic implementation
        request = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
        
        # V2 Future: Add tools support
        # request["tools"] = [...]
        # request["tool_choice"] = "auto"
        
        return request