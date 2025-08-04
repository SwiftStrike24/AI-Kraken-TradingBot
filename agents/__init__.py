"""
Multi-Agent Trading System

This package contains the specialized AI agents that collectively manage
the crypto trading bot's decision-making process.

Each agent has a specific cognitive role:
- SupervisorAgent: Orchestrates the entire pipeline and ensures shared context
- AnalystAgent: Gathers and processes market intelligence
- StrategistAgent: Builds sophisticated prompts for the AI decision engine
- TraderAgent: Executes AI calls and parses trading decisions
- CoinGeckoAgent: Provides real-time cryptocurrency market data and trends

All agents follow the same interface pattern:
1. log_thoughts() - Records internal reasoning
2. execute() - Performs the agent's core function
3. Standardized JSON input/output for communication
"""

from .base_agent import BaseAgent
from .supervisor_agent import SupervisorAgent
from .analyst_agent import AnalystAgent
from .strategist_agent import StrategistAgent
from .trader_agent import TraderAgent
from .coingecko_agent import CoinGeckoAgent

__all__ = ['BaseAgent', 'SupervisorAgent', 'AnalystAgent', 'StrategistAgent', 'TraderAgent', 'CoinGeckoAgent']