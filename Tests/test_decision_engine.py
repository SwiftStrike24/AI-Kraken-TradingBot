import unittest
import json
from unittest.mock import patch, MagicMock, mock_open

# Set dummy env var for testing before importing the class
import os
os.environ['OPENAI_API_KEY'] = 'dummy_openai_key'

from bot.decision_engine import DecisionEngine, DecisionEngineError
from bot.kraken_api import KrakenAPI

class TestDecisionEngine(unittest.TestCase):
    """Unit tests for the DecisionEngine class."""

    def setUp(self):
        """Set up a mock KrakenAPI and a new DecisionEngine instance for each test."""
        self.mock_kraken_api = MagicMock(spec=KrakenAPI)
        self.engine = DecisionEngine(self.mock_kraken_api)

    def test_initialization_success(self):
        """Test that the DecisionEngine initializes correctly."""
        self.assertIsInstance(self.engine.kraken_api, MagicMock)
        self.assertIsNotNone(self.engine.client)

    @patch('bot.decision_engine.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="## Some other content\n---\n## All deep-research prompts\nCurrent cash: **$X USDC**.\nPrevious thesis: **(insert last thesis summary)**.\n---\nLast thesis content.")
    def test_build_prompt_with_history(self, mock_file, mock_exists):
        """Test that the prompt is built correctly when a thesis log exists."""
        mock_exists.return_value = True
        context = {
            "portfolio": "Current cash balance: $100.00 USDC.",
            "thesis": "Last thesis content."
        }
        
        prompt = self.engine._build_prompt(context)
        
        self.assertIn("Current cash balance: $100.00 USDC.", prompt)
        self.assertIn("Previous thesis: Last thesis content.", prompt)
        self.assertIn("Your entire response must be a single JSON object", prompt)
        mock_file.assert_called_with("Experiment-Details/Prompts.md", 'r')

    @patch('bot.decision_engine.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="Last thesis from file.")
    def test_get_context_with_assets(self, mock_open, mock_exists):
        """Test getting context when the portfolio has assets."""
        # Configure the mock methods directly on the instance passed to the engine
        self.mock_kraken_api.get_account_balance.return_value = {'USDC': 100.50, 'XBT': 0.5, 'ETH': 10.0}
        self.mock_kraken_api.get_ticker_prices.return_value = {
            'XXBTZUSD': {'price': 60000.0},
            'XETHZUSD': {'price': 4000.0}
        }
        mock_exists.return_value = True
        
        context = self.engine._get_context()

        self.assertIn("Current cash balance: $100.50 USDC.", context['portfolio'])
        self.assertIn("XBT: 0.500000 (Value: $30,000.00 @ $60,000.00)", context['portfolio'])
        self.assertIn("ETH: 10.000000 (Value: $40,000.00 @ $4,000.00)", context['portfolio'])
        self.assertEqual(context['thesis'], "Last thesis from file.")
        
    @patch('openai.OpenAI')
    def test_generate_strategy_success(self, mock_openai):
        """Test a successful strategy generation call."""
        # Mock the context methods to provide predictable data
        self.engine._get_context = MagicMock(return_value={"portfolio": "mock portfolio", "thesis": "mock thesis"})
        self.engine._build_prompt = MagicMock(return_value="mock prompt")

        # Mock the OpenAI API response
        mock_api_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        
        # This is the JSON string the AI is expected to return
        ai_json_payload = '{"trades": [{"pair": "XBT/USD", "action": "buy", "volume": 0.01}], "thesis": "New thesis about market conditions."}'
        mock_message.content = ai_json_payload
        mock_choice.message = mock_message
        mock_api_response.choices = [mock_choice]
        
        # The mocked client's method returns the mock response
        mock_openai_instance = mock_openai.return_value
        mock_openai_instance.chat.completions.create.return_value = mock_api_response
        
        # Assign the mocked client to the engine instance
        self.engine.client = mock_openai_instance

        # Call the method under test
        strategy = self.engine.generate_strategy()

        # Assertions
        self.engine._get_context.assert_called_once()
        self.engine._build_prompt.assert_called_once_with({"portfolio": "mock portfolio", "thesis": "mock thesis"})
        mock_openai_instance.chat.completions.create.assert_called_once_with(
            model="gpt-4o",
            messages=[{"role": "user", "content": "mock prompt"}],
            response_format={"type": "json_object"}
        )
        
        self.assertEqual(strategy['thesis'], "New thesis about market conditions.")
        self.assertEqual(len(strategy['trades']), 1)
        self.assertEqual(strategy['trades'][0]['pair'], 'XBT/USD')

    @patch('openai.OpenAI')
    def test_generate_strategy_invalid_json(self, mock_openai):
        """Test that generate_strategy raises an error on malformed JSON."""
        self.engine._get_context = MagicMock(return_value={})
        self.engine._build_prompt = MagicMock(return_value="prompt")
        
        mock_api_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        
        # Malformed JSON (missing closing brace)
        mock_message.content = '{"trades": [], "thesis": "..."'
        mock_choice.message = mock_message
        mock_api_response.choices = [mock_choice]
        
        mock_openai_instance = mock_openai.return_value
        mock_openai_instance.chat.completions.create.return_value = mock_api_response
        self.engine.client = mock_openai_instance

        with self.assertRaises(DecisionEngineError) as context:
            self.engine.generate_strategy()
        
        self.assertIn("Failed to decode JSON", str(context.exception))

    @patch('openai.OpenAI')
    def test_generate_strategy_missing_keys(self, mock_openai):
        """Test that generate_strategy raises an error if the JSON is missing required keys."""
        self.engine._get_context = MagicMock(return_value={})
        self.engine._build_prompt = MagicMock(return_value="prompt")
        
        mock_api_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        
        # Valid JSON, but missing the 'thesis' key
        mock_message.content = '{"trades": []}'
        mock_choice.message = mock_message
        mock_api_response.choices = [mock_choice]
        
        mock_openai_instance = mock_openai.return_value
        mock_openai_instance.chat.completions.create.return_value = mock_api_response
        self.engine.client = mock_openai_instance

        with self.assertRaises(DecisionEngineError) as context:
            self.engine.generate_strategy()
        
        self.assertIn("missing 'trades' or 'thesis' key", str(context.exception))

if __name__ == '__main__':
    unittest.main() 