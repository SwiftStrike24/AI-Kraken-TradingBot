"""
Test Enhanced AI Prompt Integration

Tests the enhanced AI market analysis that combines:
- Real-time CoinGecko market data (quantitative)
- RSS news headlines (qualitative)
- Optimized prompt engineering (OpenAI 2025 best practices)
"""

import unittest
import json
import os
import tempfile
from unittest.mock import Mock, patch, mock_open
from datetime import datetime

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.research_agent import ResearchAgent
from agents.analyst_agent import AnalystAgent
from agents.supervisor_agent import SupervisorAgent
from bot.kraken_api import KrakenAPI

class TestEnhancedAIPrompt(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.session_dir = os.path.join(self.temp_dir, "session")
        os.makedirs(self.session_dir, exist_ok=True)
        
        # Mock OpenAI client
        self.mock_openai = Mock()
        self.mock_response = Mock()
        self.mock_response.choices = [Mock()]
        self.mock_response.choices[0].message.content = "Bitcoin shows strong institutional accumulation with +3.2% daily gains, while Ethereum's technical breakout above $3,400 resistance confirms bullish momentum. Market sentiment remains cautiously optimistic (75% confidence) with XRP leading altcoin recovery at +5.8%, though macro uncertainty from Fed policy discussions suggests maintaining 60% cash allocation for tactical opportunities."
        self.mock_openai.chat.completions.create.return_value = self.mock_response
        
        # Sample CoinGecko data
        self.sample_coingecko_data = {
            "status": "success",
            "market_data": {
                "bitcoin": {
                    "name": "Bitcoin",
                    "symbol": "BTC",
                    "current_price": 67234.56,
                    "price_change_percentage_24h": 3.2,
                    "market_cap_rank": 1
                },
                "ethereum": {
                    "name": "Ethereum", 
                    "symbol": "ETH",
                    "current_price": 3456.78,
                    "price_change_percentage_24h": 2.1,
                    "market_cap_rank": 2
                },
                "ripple": {
                    "name": "XRP",
                    "symbol": "XRP",
                    "current_price": 0.5874,
                    "price_change_percentage_24h": 5.8,
                    "market_cap_rank": 5
                }
            },
            "trending_data": {
                "coins": [
                    {"item": {"name": "Fartcoin", "symbol": "FARTCOIN", "market_cap_rank": 89}},
                    {"item": {"name": "Bonk", "symbol": "BONK", "market_cap_rank": 45}},
                    {"item": {"name": "Sui", "symbol": "SUI", "market_cap_rank": 18}}
                ]
            },
            "data_quality": {"quality_score": "excellent"}
        }
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_coingecko_data_formatting_for_ai(self):
        """Test that CoinGecko data is properly formatted for AI consumption."""
        research_agent = ResearchAgent(
            openai_api_key="test_key",
            logs_dir=self.temp_dir
        )
        research_agent.openai_client = self.mock_openai
        
        formatted_text = research_agent._format_coingecko_for_ai(self.sample_coingecko_data)
        
        # Verify price data is included
        self.assertIn("LIVE PRICE DATA:", formatted_text)
        self.assertIn("Bitcoin (BTC): $67,234.56", formatted_text)
        self.assertIn("📈 +3.20%", formatted_text)  # Positive change indicator
        self.assertIn("Rank #1", formatted_text)
        
        # Verify trending data is included
        self.assertIn("TRENDING NOW:", formatted_text)
        self.assertIn("1. Fartcoin (FARTCOIN)", formatted_text)
        self.assertIn("2. Bonk (BONK)", formatted_text)
        
        # Verify data quality
        self.assertIn("DATA QUALITY: EXCELLENT", formatted_text)
    
    def test_enhanced_prompt_structure(self):
        """Test that the enhanced prompt follows OpenAI 2025 best practices."""
        research_agent = ResearchAgent(
            openai_api_key="test_key",
            logs_dir=self.temp_dir
        )
        research_agent.openai_client = self.mock_openai
        
        # Mock news data
        with patch.object(research_agent, '_fetch_crypto_news', return_value=[
            "[Cointelegraph] Bitcoin hits new institutional adoption milestone",
            "[CoinDesk] Ethereum upgrade shows promising scalability improvements"
        ]):
            with patch.object(research_agent, '_fetch_macro_news', return_value=[
                "[Reuters] Fed considers policy adjustments amid crypto growth",
                "[WSJ] Regulatory clarity emerges for digital assets"
            ]):
                # Test the market summary with CoinGecko data
                result = research_agent._fetch_market_summary(self.sample_coingecko_data)
                
                # Verify OpenAI was called with enhanced prompt
                self.mock_openai.chat.completions.create.assert_called_once()
                call_args = self.mock_openai.chat.completions.create.call_args
                
                # Check system prompt enhancement
                system_prompt = call_args[1]['messages'][0]['content']
                self.assertIn("senior cryptocurrency portfolio manager", system_prompt)
                self.assertIn("quantitative analyst", system_prompt)
                self.assertIn("institutional trading strategies", system_prompt)
                
                # Check user prompt structure
                user_prompt = call_args[1]['messages'][1]['content']
                self.assertIn("ROLE:", user_prompt)
                self.assertIn("TASK:", user_prompt)
                self.assertIn("DATA SOURCES:", user_prompt)
                self.assertIn("QUANTITATIVE MARKET DATA:", user_prompt)
                self.assertIn("QUALITATIVE NEWS INTELLIGENCE", user_prompt)
                self.assertIn("OUTPUT REQUIREMENTS:", user_prompt)
                self.assertIn("SPECIFIC DELIVERABLES:", user_prompt)
                
                # Verify CoinGecko data is in the prompt
                self.assertIn("Bitcoin (BTC): $67,234.56", user_prompt)
                self.assertIn("📈 +3.20%", user_prompt)
                
                # Verify targeting and specificity improvements
                self.assertIn("institutional crypto traders", user_prompt)
                self.assertIn("portfolio managers", user_prompt)
                self.assertIn("BTC, ETH, SOL, ADA, XRP, SUI, ENA, DOGE, FARTCOIN, BONK", user_prompt)
                self.assertIn("confidence level", user_prompt)
                self.assertIn("4-5 flowing sentences", user_prompt)
    
    def test_analyst_agent_coingecko_integration(self):
        """Test that AnalystAgent properly receives and uses CoinGecko data."""
        # Create AnalystAgent with mocked ResearchAgent
        analyst = AnalystAgent(logs_dir=self.temp_dir, session_dir=self.session_dir)
        
        # Mock the research engine
        analyst.research_engine = Mock()
        analyst.research_engine.generate_daily_report.return_value = "# Market Analysis\n\nBitcoin showing strength with institutional flows..."
        
        # Test inputs with CoinGecko data
        test_inputs = {
            "research_focus": "crypto_market_analysis",
            "coingecko_data": self.sample_coingecko_data,
            "supervisor_directives": {"risk_level": "moderate"}
        }
        
        result = analyst.execute(test_inputs)
        
        # Verify CoinGecko data was passed to research engine
        analyst.research_engine.generate_daily_report.assert_called_once_with(
            self.sample_coingecko_data
        )
        
        # Verify successful execution
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["agent"], "Analyst-AI")
        self.assertIn("research_report", result)
    
    @patch('agents.supervisor_agent.KrakenAPI')
    def test_supervisor_pipeline_integration(self, mock_kraken):
        """Test that the SupervisorAgent correctly passes CoinGecko data through the pipeline."""
        # Mock KrakenAPI
        mock_kraken_instance = Mock()
        mock_kraken.return_value = mock_kraken_instance
        
        supervisor = SupervisorAgent(
            kraken_api=mock_kraken_instance,
            logs_dir=self.temp_dir,
            session_dir=self.session_dir
        )
        
        # Mock the individual agents
        supervisor.coingecko = Mock()
        supervisor.coingecko.run.return_value = self.sample_coingecko_data
        
        supervisor.analyst = Mock()
        supervisor.analyst.run.return_value = {
            "status": "success",
            "research_report": {"market_summary": "Enhanced analysis with CoinGecko data"}
        }
        
        supervisor.strategist = Mock()
        supervisor.strategist.run.return_value = {"status": "success", "prompt_payload": "test"}
        
        supervisor.trader = Mock()
        supervisor.trader.run.return_value = {"status": "success", "trading_decision": "hold"}
        
        # Test pipeline execution
        test_inputs = {"token_ids": ["bitcoin", "ethereum", "ripple"]}
        
        # Execute just the CoinGecko and Analyst stages
        coingecko_result = supervisor._run_coingecko_stage(test_inputs)
        analyst_result = supervisor._run_analyst_stage(coingecko_result, test_inputs)
        
        # Verify CoinGecko data flows to Analyst
        analyst_call_args = supervisor.analyst.run.call_args[0][0]
        self.assertEqual(analyst_call_args["coingecko_data"], self.sample_coingecko_data)
        self.assertIn("coingecko_execution_context", analyst_call_args)
    
    def test_prompt_optimization_elements(self):
        """Test that all OpenAI optimization suggestions are implemented."""
        research_agent = ResearchAgent(
            openai_api_key="test_key",
            logs_dir=self.temp_dir
        )
        research_agent.openai_client = self.mock_openai
        
        with patch.object(research_agent, '_fetch_crypto_news', return_value=["Test news"]):
            with patch.object(research_agent, '_fetch_macro_news', return_value=["Test macro"]):
                research_agent._fetch_market_summary(self.sample_coingecko_data)
                
                user_prompt = self.mock_openai.chat.completions.create.call_args[1]['messages'][1]['content']
                
                # Check OpenAI optimization suggestions are addressed:
                
                # 1. Specific cryptocurrencies mentioned
                self.assertIn("BTC, ETH, SOL, ADA, XRP, SUI, ENA, DOGE, FARTCOIN, BONK", user_prompt)
                
                # 2. Preferred output format specified
                self.assertIn("4-5 flowing sentences without bullet points", user_prompt)
                
                # 3. Update frequency indicated
                self.assertIn("Daily market open assessment", user_prompt)
                
                # 4. Target audience specified
                self.assertIn("Institutional crypto traders and portfolio managers", user_prompt)
                
                # 5. Analysis type specified
                self.assertIn("Combined fundamental sentiment + technical price action + quantitative metrics", user_prompt)

if __name__ == '__main__':
    unittest.main() 