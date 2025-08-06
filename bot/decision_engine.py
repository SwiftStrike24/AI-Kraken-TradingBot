import os
import json
import logging
from openai import OpenAI, APIError

from bot.kraken_api import KrakenAPI
from bot.prompt_engine import PromptEngine, PromptEngineError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DecisionEngineError(Exception):
    """Custom exception for errors within the Decision Engine."""
    pass

class DecisionEngine:
    """
    The "brain" of the trading bot. It queries the OpenAI API to get a trading strategy.
    """
    def __init__(self, kraken_api: KrakenAPI):
        """
        Initializes the DecisionEngine.
        
        Args:
            kraken_api: An instance of the KrakenAPI client.
        """
        self.kraken_api = kraken_api
        try:
            self.client = OpenAI() # API key is loaded automatically from OPENAI_API_KEY env var
        except Exception as e:
            raise DecisionEngineError(f"Failed to initialize OpenAI client: {e}")
        
        # Initialize the advanced prompt engine
        try:
            self.prompt_engine = PromptEngine()
        except PromptEngineError as e:
            raise DecisionEngineError(f"Failed to initialize PromptEngine: {e}")
        
        # Define paths for logs
        self.thesis_log_path = "logs/thesis_log.md"

    def _get_context(self) -> dict:
        """
        Fetches all dynamic data required for building the prompt using live Kraken API data.

        Returns:
            A dictionary containing comprehensive portfolio status and historical thesis.
        """
        try:
            # Get comprehensive portfolio data from Kraken API (never assume, always query live)
            portfolio_data = self.kraken_api.get_comprehensive_portfolio_context()
            
            logger.info(f"Live portfolio retrieved: Total equity ${portfolio_data['total_equity']:,.2f}")
            logger.info(f"Tradeable assets: {portfolio_data['tradeable_assets']}")
            
            # Get the last thesis
            if os.path.exists(self.thesis_log_path):
                with open(self.thesis_log_path, 'r', encoding='utf-8') as f:
                    # Read all theses and grab the last one. Assumes theses are separated by '---'.
                    theses = f.read().split('---')
                    last_thesis = theses[-1].strip() if theses else "No previous thesis found."
            else:
                last_thesis = "No previous thesis found."

            return {
                'portfolio': portfolio_data['portfolio_summary'],
                'portfolio_data': portfolio_data,  # Full data for advanced logic
                'thesis': last_thesis
            }
            
        except Exception as e:
            logger.error(f"Error getting context: {e}")
            raise DecisionEngineError(f"Could not get context: {e}")



    def generate_strategy(self, research_report: str = "") -> dict:
        """
        Builds the prompt using PromptEngine, queries the OpenAI API, and returns a structured trading plan.

        Args:
            research_report: Market research report from ResearchAgent.

        Returns:
            A dictionary containing the AI's trading plan and new thesis.
            Example: {'trades': [{'pair': 'XBT/USD', 'action': 'buy', 'volume': 0.1}], 'thesis': '...'}
        """
        try:
            # Get context and build prompt using the advanced PromptEngine
            context = self._get_context()
            
            # Use the PromptEngine's build_openai_request method for proper message structure
            request_obj = self.prompt_engine.build_openai_request(
                portfolio_context=context['portfolio'],
                research_report=research_report,
                last_thesis=context['thesis']
            )
            
            logger.info("Generating AI strategy using PromptEngine. Sending structured request to OpenAI...")
            logger.debug(f"Request structure: {len(request_obj['messages'])} messages")

            # Call OpenAI API with the structured request
            response = self.client.chat.completions.create(**request_obj)
            
            response_content = response.choices[0].message.content
            logger.info("Received raw response from OpenAI.")
            logger.debug(f"Raw response content:\n{response_content}")

            # Parse and validate the response
            decision = json.loads(response_content)
            
            if 'trades' not in decision or 'thesis' not in decision:
                raise DecisionEngineError("AI response is missing 'trades' or 'thesis' key.")

            logger.info("Successfully parsed AI strategy.")
            return decision

        except PromptEngineError as e:
            logger.error(f"PromptEngine error: {e}")
            raise DecisionEngineError(f"PromptEngine error: {e}")
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise DecisionEngineError(f"OpenAI API error: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from OpenAI response: {e}")
            raise DecisionEngineError(f"Failed to decode JSON from OpenAI response. Raw content: {response_content}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during strategy generation: {e}")
            raise DecisionEngineError(f"An unexpected error occurred: {e}")
