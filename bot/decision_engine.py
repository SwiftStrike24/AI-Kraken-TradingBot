import os
import json
import logging
from openai import OpenAI, APIError

from bot.kraken_api import KrakenAPI

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
        
        # Define paths for prompt templates and logs
        self.prompt_template_path = "Experiment-Details/Prompts.md"
        self.thesis_log_path = "logs/thesis_log.md"

    def _get_context(self) -> dict:
        """
        Fetches all dynamic data required for building the prompt.

        Returns:
            A dictionary containing portfolio status and historical thesis.
        """
        try:
            # 1. Get current portfolio from Kraken
            balance = self.kraken_api.get_account_balance()
            if not balance:
                portfolio_context = "Portfolio is currently empty. Cash on hand: 0 USDC."
            else:
                # Handle cash balances (treat as $1.00 per unit for USD-denominated assets)
                cash_assets = {'USDC', 'USD', 'USDT'}
                total_cash = 0.0
                
                for cash_asset in cash_assets:
                    if cash_asset in balance:
                        total_cash += balance.pop(cash_asset, 0.0)
                
                portfolio_context = f"Current cash balance: ${total_cash:,.2f} USD.\n"
                
                if balance: # If there are other crypto assets (excluding fiat)
                    # Filter out forex assets that we don't want to trade
                    forex_assets = {'CAD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'SEK', 'NOK', 'DKK'}
                    crypto_assets = [asset for asset in balance.keys() if asset not in forex_assets]
                    
                    logger.info(f"Crypto assets in balance: {crypto_assets}")
                    if forex_assets.intersection(balance.keys()):
                        logger.info(f"Forex assets found (excluded from trading): {forex_assets.intersection(balance.keys())}")
                    
                    if crypto_assets:
                        valid_pairs = self.kraken_api.get_valid_usd_pairs_for_assets(crypto_assets)
                        logger.info(f"Valid USD pairs found: {valid_pairs}")
                        
                        if valid_pairs:
                            prices = self.kraken_api.get_ticker_prices(valid_pairs)
                            logger.info(f"Price data received for {len(prices)} pairs")
                            
                            portfolio_context += "Current Holdings:\n"
                            for asset, amount in balance.items():
                                if asset in crypto_assets:
                                    # Find the corresponding USD pair for this crypto asset
                                    asset_pair = self.kraken_api.asset_to_usd_pair_map.get(asset)
                                    if asset_pair and asset_pair in prices:
                                        price = prices[asset_pair]['price']
                                        value = amount * price
                                        portfolio_context += f"- {asset}: {amount:.6f} (Value: ${value:,.2f} @ ${price:,.2f})\n"
                                    else:
                                        portfolio_context += f"- {asset}: {amount:.6f} (No USD pair available)\n"
                                        logger.warning(f"No valid USD pair found for crypto asset: {asset}")
                                else:
                                    # For forex assets, just show the amount without valuation
                                    portfolio_context += f"- {asset}: {amount:.6f} (Forex - not traded)\n"
                        else:
                            portfolio_context += "Current Holdings:\n"
                            for asset, amount in balance.items():
                                if asset in crypto_assets:
                                    portfolio_context += f"- {asset}: {amount:.6f} (No USD pair available)\n"
                                else:
                                    portfolio_context += f"- {asset}: {amount:.6f} (Forex - not traded)\n"
                            logger.warning("No valid USD pairs found for any crypto assets in balance")
                    else:
                        # Only forex assets remain
                        if balance:
                            portfolio_context += "Current Holdings:\n"
                            for asset, amount in balance.items():
                                portfolio_context += f"- {asset}: {amount:.6f} (Forex - not traded)\n"
                else:
                    portfolio_context += "No crypto assets held."

            # 2. Get the last thesis
            if os.path.exists(self.thesis_log_path):
                with open(self.thesis_log_path, 'r', encoding='utf-8') as f:
                    # Read all theses and grab the last one. Assumes theses are separated by '---'.
                    theses = f.read().split('---')
                    last_thesis = theses[-1].strip() if theses else "No previous thesis found."
            else:
                last_thesis = "No thesis log found. This is the first run."

            return {"portfolio": portfolio_context, "thesis": last_thesis}

        except Exception as e:
            logger.error(f"Error getting context: {e}")
            raise DecisionEngineError(f"Could not get context: {e}")

    def _build_prompt(self, context: dict) -> str:
        """
        Assembles the final prompt using a template and dynamic context.

        Args:
            context: A dictionary with 'portfolio' and 'thesis' data.

        Returns:
            The complete prompt string to be sent to the AI.
        """
        with open(self.prompt_template_path, 'r', encoding='utf-8') as f:
            # Using the "deep-research" prompt as the primary template
            templates = f.read().split('##')
            prompt_template = next((p for p in templates if "All deep-research prompts" in p), "")

        if not prompt_template:
            raise FileNotFoundError("Could not find the deep-research prompt template.")
            
        # Inject dynamic data
        prompt = prompt_template.replace("Current cash: **$X USDC**.", context['portfolio'])
        prompt = prompt.replace("Previous thesis: **(insert last thesis summary)**.", f"Previous thesis: {context['thesis']}")
        
        # Add a specific instruction for the JSON output format right in the prompt
        json_format_instruction = (
            "\n\nIMPORTANT: Your entire response must be a single JSON object, without any surrounding text or markdown. "
            "The JSON object must have two keys: 'trades' and 'thesis'.\n"
            "'trades' should be a list of objects, where each object has 'pair' (e.g., 'XBT/USD'), 'action' ('buy' or 'sell'), and 'volume' (as a float).\n"
            "'thesis' should be a string containing your updated investment thesis."
        )
        prompt += json_format_instruction
        return prompt

    def generate_strategy(self) -> dict:
        """
        Builds the prompt, queries the OpenAI API, and returns a structured trading plan.

        Returns:
            A dictionary containing the AI's trading plan and new thesis.
            Example: {'trades': [{'pair': 'XBT/USD', 'action': 'buy', 'volume': 0.1}], 'thesis': '...'}
        """
        context = self._get_context()
        prompt = self._build_prompt(context)
        
        logger.info("Generating AI strategy. Sending prompt to OpenAI...")
        logger.debug(f"Full prompt:\n{prompt}")

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            response_content = response.choices[0].message.content
            logger.info("Received raw response from OpenAI.")
            logger.debug(f"Raw response content:\n{response_content}")

            decision = json.loads(response_content)
            
            # Basic validation of the returned structure
            if 'trades' not in decision or 'thesis' not in decision:
                raise DecisionEngineError("AI response is missing 'trades' or 'thesis' key.")

            logger.info("Successfully parsed AI strategy.")
            return decision

        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise DecisionEngineError(f"OpenAI API error: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from OpenAI response: {e}")
            raise DecisionEngineError(f"Failed to decode JSON from OpenAI response. Raw content: {response_content}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during strategy generation: {e}")
            raise DecisionEngineError(f"An unexpected error occurred: {e}")
