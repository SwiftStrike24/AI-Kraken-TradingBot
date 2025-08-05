import unittest
import os
import tempfile
import shutil
from unittest.mock import patch, mock_open

from bot.prompt_engine import PromptEngine, PromptEngineError


class TestPromptEngine(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures with a temporary directory."""
        self.test_dir = tempfile.mkdtemp()
        self.test_template_path = os.path.join(self.test_dir, "test_template.md")
        
        # Create a test template
        self.test_template_content = """<SYSTEM_INSTRUCTIONS>
You are a test trading bot.
</SYSTEM_INSTRUCTIONS>

<CONTEXT>
  <PORTFOLIO_STATE>
    {portfolio_context}
  </PORTFOLIO_STATE>

  <MARKET_INTELLIGENCE_REPORT>
    {research_report}
  </MARKET_INTELLIGENCE_REPORT>

  <STRATEGY_FEEDBACK_LOOP>
    <PREVIOUS_THESIS>
      {last_thesis}
    </PREVIOUS_THESIS>
    <PERFORMANCE_REVIEW>
      {performance_review}
    </PERFORMANCE_REVIEW>
  </STRATEGY_FEEDBACK_LOOP>
</CONTEXT>

<TASK>
Generate a JSON response with trades and thesis.
</TASK>"""
        
        with open(self.test_template_path, 'w', encoding='utf-8') as f:
            f.write(self.test_template_content)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_initialization_success(self):
        """Test successful PromptEngine initialization."""
        engine = PromptEngine(template_path=self.test_template_path)
        self.assertIsInstance(engine, PromptEngine)
        self.assertEqual(engine.template_path, self.test_template_path)
        self.assertIsNone(engine.max_tokens)  # Default is no limit
        self.assertIsNotNone(engine._template)
    
    def test_initialization_custom_max_tokens(self):
        """Test initialization with custom max_tokens."""
        engine = PromptEngine(template_path=self.test_template_path, max_tokens=5000)
        self.assertEqual(engine.max_tokens, 5000)
    
    def test_initialization_missing_template(self):
        """Test initialization with missing template file."""
        non_existent_path = os.path.join(self.test_dir, "missing.md")
        with self.assertRaises(PromptEngineError) as context:
            PromptEngine(template_path=non_existent_path)
        self.assertIn("Prompt template not found", str(context.exception))
    
    def test_load_template_success(self):
        """Test successful template loading."""
        engine = PromptEngine(template_path=self.test_template_path)
        self.assertEqual(engine._template, self.test_template_content)
    
    def test_estimate_tokens(self):
        """Test token estimation function."""
        engine = PromptEngine(template_path=self.test_template_path)
        
        # Test with various text lengths
        short_text = "Hello"
        estimated = engine._estimate_tokens(short_text)
        self.assertEqual(estimated, 1)  # 5 chars / 4 = 1.25 -> 1
        
        long_text = "A" * 400  # 400 characters
        estimated = engine._estimate_tokens(long_text)
        self.assertEqual(estimated, 100)  # 400 / 4 = 100
    
    def test_truncate_text_no_truncation_needed(self):
        """Test text truncation when no truncation is needed."""
        engine = PromptEngine(template_path=self.test_template_path, max_tokens=1000)
        short_text = "This is a short text that doesn't need truncation."
        
        result = engine._truncate_text(short_text)
        self.assertEqual(result, short_text)
    
    def test_truncate_text_empty_input(self):
        """Test text truncation with empty input."""
        engine = PromptEngine(template_path=self.test_template_path)
        
        result = engine._truncate_text("")
        self.assertEqual(result, "")
        
        result = engine._truncate_text("   ")
        self.assertEqual(result, "   ")
    
    def test_truncate_text_truncation_needed(self):
        """Test text truncation when truncation is required."""
        engine = PromptEngine(template_path=self.test_template_path, max_tokens=50)
        
        # Create a long text that will need truncation
        lines = [f"Line {i}: This is a test line with some content." for i in range(50)]
        long_text = '\n'.join(lines)
        
        result = engine._truncate_text(long_text)
        
        # Should be shorter than original
        self.assertLess(len(result), len(long_text))
        # Should contain truncation notice
        self.assertIn("truncated", result.lower())
        # Should preserve some header content
        self.assertIn("Line 0:", result)
    
    def test_generate_performance_review(self):
        """Test performance review generation (V1 placeholder)."""
        engine = PromptEngine(template_path=self.test_template_path)
        
        review = engine._generate_performance_review()
        self.assertIsInstance(review, str)
        self.assertGreater(len(review), 0)
        self.assertIn("No performance data available", review)
    
    def test_build_prompt_success(self):
        """Test successful prompt building with all context."""
        engine = PromptEngine(template_path=self.test_template_path)
        
        portfolio_context = "Cash: $100 USD. Holdings: 0.01 BTC @ $60,000"
        research_report = "Bitcoin showing strong momentum today."
        last_thesis = "Maintaining BTC position for long-term gains."
        
        result = engine.build_prompt(portfolio_context, research_report, last_thesis)
        
        # Check that all context was injected
        self.assertIn(portfolio_context, result)
        self.assertIn(research_report, result)
        self.assertIn(last_thesis, result)
        self.assertIn("No performance data available", result)  # Performance review placeholder
        
        # Check template structure is preserved
        self.assertIn("SYSTEM_INSTRUCTIONS", result)
        self.assertIn("CONTEXT", result)
        self.assertIn("TASK", result)
    
    def test_build_prompt_with_long_research_report(self):
        """Test prompt building with research report that needs truncation."""
        engine = PromptEngine(template_path=self.test_template_path, max_tokens=100)
        
        portfolio_context = "Cash: $100 USD"
        # Create a very long research report
        long_research = "Very long research report. " * 200
        last_thesis = "Test thesis"
        
        result = engine.build_prompt(portfolio_context, long_research, last_thesis)
        
        # Should still build successfully
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        # Should contain portfolio context
        self.assertIn(portfolio_context, result)
        # Research should be truncated
        self.assertLess(len(result), len(self.test_template_content) + len(long_research))
    
    def test_build_prompt_missing_template_variable(self):
        """Test prompt building with missing template variables."""
        # Create template with unknown variable
        bad_template_path = os.path.join(self.test_dir, "bad_template.md")
        with open(bad_template_path, 'w', encoding='utf-8') as f:
            f.write("Template with {unknown_variable}")
        
        engine = PromptEngine(template_path=bad_template_path)
        
        with self.assertRaises(PromptEngineError) as context:
            engine.build_prompt("portfolio", "research", "thesis")
        
        self.assertIn("Missing template variable", str(context.exception))
    
    @patch('builtins.open', new_callable=mock_open)
    def test_log_prompt(self, mock_file):
        """Test prompt logging functionality."""
        engine = PromptEngine(template_path=self.test_template_path)
        test_prompt = "This is a test prompt"
        
        # Should not raise any exceptions
        engine._log_prompt(test_prompt)
        
        # Verify file was opened for writing
        mock_file.assert_called()
        # Check that write was called with prompt content
        written_content = ''.join(call.args[0] for call in mock_file().write.call_args_list)
        self.assertIn(test_prompt, written_content)
        self.assertIn("PROMPT LOG", written_content)
    
    def test_build_openai_request_basic(self):
        """Test building OpenAI request object (V1 implementation)."""
        engine = PromptEngine(template_path=self.test_template_path)
        
        portfolio_context = "Cash: $100 USD"
        research_report = "Market is bullish"
        last_thesis = "Hold BTC"
        
        request = engine.build_openai_request(portfolio_context, research_report, last_thesis)
        
        # Check request structure
        self.assertIsInstance(request, dict)
        self.assertIn("model", request)
        self.assertIn("messages", request)
        self.assertIn("response_format", request)
        
        # Check specific values
        self.assertEqual(request["model"], "gpt-4o")
        self.assertEqual(request["response_format"], {"type": "json_object"})
        self.assertIsInstance(request["messages"], list)
        self.assertEqual(len(request["messages"]), 1)
        self.assertEqual(request["messages"][0]["role"], "user")
        
        # Check that prompt content is in the message
        message_content = request["messages"][0]["content"]
        self.assertIn(portfolio_context, message_content)
        self.assertIn(research_report, message_content)
        self.assertIn(last_thesis, message_content)
    
    def test_build_openai_request_custom_model(self):
        """Test building OpenAI request with custom model."""
        engine = PromptEngine(template_path=self.test_template_path)
        
        request = engine.build_openai_request(
            "portfolio", "research", "thesis", model="gpt-4-turbo"
        )
        
        self.assertEqual(request["model"], "gpt-4-turbo")
    
    def test_prompt_logs_directory_creation(self):
        """Test that prompt logs directory is created."""
        # Use a fresh temp directory
        logs_dir = os.path.join(self.test_dir, "test_logs")
        prompt_logs_dir = os.path.join(logs_dir, "prompts")
        
        # Directory shouldn't exist initially
        self.assertFalse(os.path.exists(prompt_logs_dir))
        
        # Initialize engine (should create directory)
        engine = PromptEngine(template_path=self.test_template_path)
        engine.prompt_logs_dir = prompt_logs_dir
        engine._log_prompt("test")
        
        # Directory should now exist
        self.assertTrue(os.path.exists(prompt_logs_dir))


if __name__ == '__main__':
    unittest.main()