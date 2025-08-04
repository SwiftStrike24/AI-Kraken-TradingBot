
# ChatGPT-Kraken Portfolio Bot — Initial Implementation

## 🧠 Concept

A fully autonomous crypto trading bot powered by ChatGPT 4o with institutional-grade market intelligence.
It runs daily at 07:00 AM MST, evaluates the market using real-time data and comprehensive news analysis, and rebalances a portfolio of Kraken-listed tokens with the goal of generating consistent alpha vs BTC and ETH.
The strategy is experimental, transparent, and performance-logged.

## ⚡ Latest Enhancements (August 2025)

**🚀 Major Upgrade:** Multi-agent architecture with real-time market data integration and institutional-grade AI analysis

**Key Improvements:**
- **CoinGecko Integration:** Live price data, trending analysis, and market metrics for 10 tracked cryptocurrencies
- **Enhanced Keyword Intelligence:** 57 crypto + 81 macro keywords capturing ETFs, institutional flows, Fed policy, and regulatory developments
- **OpenAI 2025 Best Practices:** Professional prompt optimization with role definition, task specificity, and institutional output format
- **Multi-Source Intelligence:** Combines quantitative CoinGecko data with qualitative news analysis for superior market context
- **Comprehensive Coverage:** Now captures BlackRock ETF flows, MicroStrategy moves, Fed decisions, GENIUS/CLARITY Act developments, and macro trends
- **Professional Analysis:** Institutional morning briefing format with confidence levels and specific trading opportunities

---

## 🗓️ Start Date

**July 30, 2025**
Initial balance: **\$100.00 USDC**

---

## ⚙️ Architecture Overview

### Legacy Monolithic Architecture (Pre-August 2025)
```
Scheduler (daily)
   └── Research Agent → Gather market intelligence (news, sentiment, macro)
       └── Kraken API → Get balance + token prices
           └── Build ChatGPT prompt (with market context)
               └── Call OpenAI API
                   └── Parse response (BUY/SELL plan)
                       └── Execute trades via Kraken API
                           └── Log to CSV + update equity curve
```

### New Multi-Agent Architecture (August 2025+)
```
Scheduler (daily)
   └── Supervisor-AI (Central Orchestrator)
       ├── CoinGecko-AI → Real-Time Market Data & Price Intelligence
       │   ├── Live Cryptocurrency Prices, Market Caps & Volume Data (10 tokens: BTC, ETH, SOL, ADA, XRP, SUI, ENA, DOGE, FARTCOIN, BONK)
       │   ├── Trending Tokens Analysis (Top 15 trending coins)
       │   ├── Price Change Analytics (1h, 24h, 7d, 30d)
       │   └── Intelligent Caching & Rate Limiting
       ├── Analyst-AI → Market Intelligence & Sentiment Analysis (Enhanced with CoinGecko Data)
       │   ├── RSS Feed Aggregation (Crypto + Macro News from Unbiased/Right-leaning Sources)
       │   ├── Enhanced Keyword Filtering (57 crypto + 81 macro keywords including ETFs, institutions, Fed policy)
       │   ├── Real-Time Price Data Integration (from CoinGecko-AI)
       │   ├── AI-Powered Market Summary (GPT-4o with Quantitative + Qualitative Context)
       │   ├── Keyword Filtering & Content Processing  
       │   └── Structured Intelligence Reports
       ├── Strategist-AI → Advanced Prompt Engineering
       │   ├── Portfolio Context Assembly
       │   ├── Performance History Integration
       │   ├── CoinGecko Market Data Integration
       │   └── Optimized AI Prompt Construction
       ├── Trader-AI → AI Execution & Decision Parsing
       │   ├── OpenAI API Calls (GPT-4o)
       │   ├── Response Validation & Parsing
       │   └── Quality Assessment & Risk Analysis
       └── Final Review & Trade Execution
           ├── Supervisor Validation & Approval
           ├── Trade Execution (if approved)
           └── Performance Tracking & Cognitive Logging
```

---

## 🧰 Technologies Used

* **Python 3.11**
* OpenAI API (ChatGPT 4o)
* Kraken API (REST via `krakenex`)
* `pandas` for data
* `schedule` for daily automation
* `.env` for secret key handling
* `matplotlib` for equity curve tracking
* `feedparser` & `requests` for RSS news aggregation
* Local CSV-based logs for trades and PnL

---

## 📂 Project Structure

### Legacy Structure (Pre-August 2025)
```
chatgpt-kraken-bot/
├── bot/
│   ├── kraken_api.py
│   ├── decision_engine.py        # ⚠️ DEPRECATED - replaced by Trader-AI
│   ├── trade_executor.py
│   ├── performance_tracker.py
│   ├── research_agent.py         # ⚠️ DEPRECATED - replaced by Analyst-AI  
│   └── prompt_engine.py          # ⚠️ DEPRECATED - replaced by Strategist-AI
├── Tests/ [legacy test files]
├── logs/ [CSV logs]
├── scheduler.py                  # ⚠️ DEPRECATED - use scheduler_multiagent.py
└── run_trading_demo.py           # ⚠️ DEPRECATED - use run_multiagent_demo.py
```

### New Multi-Agent Structure (August 2025+)
```
chatgpt-kraken-bot/
├── agents/                       # 🆕 MULTI-AGENT SYSTEM
│   ├── __init__.py
│   ├── base_agent.py            # Common agent functionality
│   ├── supervisor_agent.py      # Central orchestrator
│   ├── analyst_agent.py         # Market intelligence specialist
│   ├── strategist_agent.py      # Prompt engineering specialist
│   └── trader_agent.py          # AI execution specialist
├── bot/                         # Core trading infrastructure
│   ├── kraken_api.py            # ✅ ACTIVE
│   ├── trade_executor.py        # ✅ ACTIVE  
│   ├── performance_tracker.py   # ✅ ACTIVE
│   └── [deprecated modules]
├── logs/
│   ├── agent_transcripts/       # 🆕 Cognitive audit trails
│   │   └── {YYYY-MM-DD}/
│   │       ├── analyst_thoughts_{timestamp}.json
│   │       ├── analyst_output_{timestamp}.json
│   │       ├── strategist_thoughts_{timestamp}.json
│   │       ├── strategist_output_{timestamp}.json
│   │       ├── trader_thoughts_{timestamp}.json
│   │       ├── trader_output_{timestamp}.json
│   │       ├── supervisor_thoughts_{timestamp}.json
│   │       └── supervisor_output_{timestamp}.json
│   ├── trades.csv               # ✅ ACTIVE
│   ├── equity.csv               # ✅ ACTIVE
│   ├── thesis_log.md            # ✅ ACTIVE
│   ├── daily_research_report.md # ✅ ACTIVE
│   ├── scheduler_multiagent.log # 🆕 Multi-agent logs
│   └── research_cache.json      # ✅ ACTIVE
├── Tests/                       # 🔄 TO BE UPDATED for multi-agent
├── .env
├── requirements.txt
├── scheduler_multiagent.py      # 🆕 NEW PRODUCTION SCHEDULER
├── run_multiagent_demo.py       # 🆕 NEW DEMO RUNNER
├── README.md
└── IMPLEMENTATION.md            # 🔄 UPDATED DOCUMENTATION
```

---

## 📌 Execution Cycle

* Runs: **7 days/week at 7:00 AM MST**
* Research agent gathers market intelligence:

  * Crypto news headlines (RSS feeds)
  * Macro/regulatory updates
  * Market sentiment indicators
* Decision engine builds ChatGPT prompt using:

  * Market intelligence report
  * Current holdings
  * Current price data
  * Thesis summary
* OpenAI returns portfolio actions with market awareness
* Trades executed on Kraken
* Logs updated with:

  * Daily research reports
  * Trade history
  * Daily portfolio value
  * Thesis evolution

---

## ✨ Performance Objective

Beat BTC and ETH on a risk-adjusted basis over the 6-month window.
Primary metric: **Total return** & **Sharpe ratio** vs BTC benchmark.

---

## ⏰ Timeline

| Milestone               | Target Date   | Status      |
| ----------------------- | ------------- |-------------|
| Folder Scaffold Done    | July 30, 2025 | ✅ Done     |
| Prompt Engine Finalized | July 30, 2025 | ⏳ Pending  |
| Kraken API Integration  | July 30, 2025 | ✅ Done     |
| First Live Run          | TBA           | ⏳ Pending  |
| Weekly Equity Review    | Every Sunday  | ⏳ Pending  |

---

## 📦 Module Status

| Module                     | Status      | Notes                                                                               |
| -------------------------- | ----------- | ----------------------------------------------------------------------------------- |
| `bot/kraken_api.py`        | ✅ Complete | Fully implemented with robust asset pair handling. Fetches valid trading pairs on init and provides asset-to-pair mapping. |
| `Tests/test_kraken_api.py` | ⚠️ Needs Update | Needs updates to test new asset pair fetching functionality.           |
| `bot/prompt_engine.py`     | ✅ Complete | **NEW:** Advanced prompt engineering module with template management, intelligent truncation, and future-proofing for performance feedback loops. |
| `Tests/test_prompt_engine.py` | ✅ Complete | **NEW:** Comprehensive tests for all prompt engine functionality including truncation, logging, and error handling. |
| `bot/decision_engine.py`   | ✅ Complete | Refactored to delegate prompt creation to PromptEngine for improved modularity and advanced prompt engineering capabilities. |
| `Tests/test_decision_engine.py` | ⚠️ Needs Update | Needs updates to test new PromptEngine integration.         |
| `bot/trade_executor.py`    | ✅ Complete | Executes AI's trade plan using a safe, two-phase (validate-then-execute) process. |
| `Tests/test_trade_executor.py` | ✅ Complete | Verifies that trade validation, execution, and error handling work correctly.       |
| `bot/performance_tracker.py`| ✅ Complete | Uses robust asset pair validation for accurate equity calculations.               |
| `Tests/test_performance_tracker.py` | ⚠️ Needs Update | Needs updates to test new asset pair handling logic.             |
| `bot/research_agent.py`    | ✅ Complete | Module that gathers market intelligence from RSS feeds and web sources.        |
| `Tests/test_research_agent.py` | ✅ Complete | Comprehensive tests for research agent functionality and error handling.         |
| `scheduler.py`             | ✅ Complete | Updated to orchestrate research agent before decision engine. Robust error handling for all modules.                      |

---

## 🔧 Recent Architecture Improvements (August 2025)

### Asset Pair Handling
- **Problem Solved:** "Unknown asset pair" errors when querying prices for assets in account balance
- **Solution:** `KrakenAPI` now fetches all valid trading pairs on initialization and creates a mapping from assets to their correct USD pair names
- **Benefits:** Eliminates guesswork, prevents API errors, supports all tradeable assets on Kraken

### Configuration Loading
- **Problem Solved:** Environment variables loaded inconsistently across modules
- **Solution:** Centralized `.env` loading at the top of `scheduler.py` before any imports
- **Benefits:** Predictable startup sequence, eliminates race conditions

### Robust Error Handling
- **Enhanced logging:** Added detailed logs showing which assets are found and which valid pairs are being used
- **Graceful degradation:** Assets without USD pairs are logged but don't crash the system
- **Fallback mechanisms:** Asset pair fetching failures fall back gracefully

### Unicode/Encoding Fix
- **Problem Solved:** Unicode decode errors when reading prompt templates and thesis files on Windows
- **Solution:** Explicitly specify UTF-8 encoding for all file operations
- **Benefits:** Cross-platform compatibility, handles emoji and special characters in files

### Fiat Currency & Forex Handling
- **Problem Solved:** Bot was trying to find USD/CHF prices for USD balances and including forex pairs
- **Solution:** 
  - Treat USD/USDC/USDT as cash at $1.00 per unit (no price lookup needed)
  - Filter out forex currencies (CAD, EUR, GBP, etc.) from crypto trading pairs
  - Exclude forex assets from equity calculations but log them for transparency
- **Benefits:** Accurate portfolio valuation, cleaner logs, no spurious API calls for forex pairs

### AI Research Agent Integration (August 2025) - ENHANCED
- **Problem Solved:** Decision engine was operating in a "portfolio vacuum" without real-world market context
- **Solution:** Added comprehensive research agent with advanced keyword filtering and CoinGecko integration
- **Enhanced Features (August 2025):**
  - **Advanced Keyword Filtering System:**
    - **57 Crypto Keywords:** Covering all tracked assets (BTC, ETH, SOL, XRP, ADA, SUI, ENA, DOGE, BONK, FARTCOIN), regulatory terms (GENIUS, CLARITY, SEC, CFTC), institutional players (BlackRock, MicroStrategy, Tesla), and trading terms
    - **81 Macro Keywords:** Comprehensive coverage of Fed policy (Powell, FOMC, rate hikes/cuts), economic indicators (CPI, employment, GDP), ETF developments, and institutional adoption
  - **Real-Time Market Data Integration:** 
    - Live price data from CoinGecko API for 10 tracked cryptocurrencies
    - Trending token analysis (Top 15 trending coins + NFTs)
    - Market cap rankings and price change analytics (1h, 24h, 7d, 30d)
    - Intelligent caching and rate limiting for API efficiency
  - **RSS Feed Aggregation** from major crypto news sources (CoinDesk, CoinTelegraph, Decrypt, etc.)
  - **Macroeconomic and regulatory news** from **full political spectrum** for balanced analysis:
    - **Centrist/Unbiased:** MarketWatch (financial news leader)
    - **Conservative/Right-leaning:** National Review, Reason Magazine, AEI, Manhattan Institute, Mises Institute  
    - **Liberal/Left-leaning:** NPR (News, All Things Considered, Planet Money), Washington Post Business, Mother Jones
  - **Enhanced AI-Powered Market Analysis:** OpenAI GPT-4o synthesizes quantitative CoinGecko data with qualitative news intelligence:
    - **Institutional-Grade Prompting:** Optimized based on OpenAI 2025 best practices with role definition, task specificity, and clear deliverables
    - **Multi-Source Intelligence:** Combines live price data, trending analysis, crypto news, and macro context
    - **Professional Output:** 4-5 sentence institutional morning briefing format with confidence levels and specific trading opportunities
    - **Risk Assessment:** Macro/regulatory risk analysis with clear directional bias for portfolio positioning
  - **Comprehensive Content Coverage:** Now captures ETF flows, Fed policy decisions, institutional adoption, regulatory developments, and market sentiment
  - Caching system to prevent duplicate processing
  - Robust error handling with graceful degradation
  - Daily research reports saved for audit trail
- **Benefits:** AI now makes trading decisions with comprehensive market awareness including quantitative data, institutional flows, regulatory changes, and balanced sentiment analysis

### Market Intelligence Pipeline
- **Stable Data Sources:** Prioritizes RSS feeds over web scraping for reliability
- **Smart Filtering:** Uses crypto and macro keyword filtering to surface relevant content
- **Rate Limiting:** Respectful request timing to avoid IP blocks
- **Error Resilience:** Individual source failures don't crash the entire research process
- **Structured Output:** Generates clean, markdown-formatted reports for AI consumption

### Advanced Prompt Engineering Architecture (August 2025) - ENHANCED
- **Problem Solved:** Monolithic prompt building was brittle and hard to maintain; AI lacked comprehensive market context
- **Solution:** Dedicated `PromptEngine` module with template-based architecture and integrated CoinGecko data
- **Enhanced Key Features (August 2025):**
  - **Professional Template System:** XML-tagged prompt structure with dedicated sections for quantitative market data and qualitative news intelligence
  - **Multi-Source Data Integration:** 
    - Real-time CoinGecko price data, trending analysis, and market metrics
    - Comprehensive news intelligence from crypto and macro sources
    - Portfolio context and performance history
    - Previous thesis and strategic context
  - **OpenAI 2025 Best Practices Implementation:**
    - **Role Definition:** "Senior cryptocurrency portfolio manager and quantitative analyst"
    - **Task Specificity:** Focus on 10 tracked cryptocurrency positions with clear deliverables
    - **Target Audience:** Institutional crypto traders and portfolio managers
    - **Output Format:** 4-5 flowing sentences suitable for institutional morning briefings
    - **Analysis Type:** Combined fundamental sentiment + technical price action + quantitative metrics
  - **Intelligent Truncation:** Smart research report truncation preserving header and recent content while maintaining 3000-token limit
  - **Enhanced Context Assembly:** CoinGecko market data formatted for AI consumption with price direction indicators and trending analysis
  - **Performance Feedback Loop:** Infrastructure for thesis accuracy tracking (V2 enhancement)
  - **Comprehensive Logging:** All prompts logged with timestamps for debugging and audit
  - **Future-Proofing:** Ready for OpenAI tool use and function calling integration
- **Benefits:** Dramatically improved AI response quality with institutional-grade market intelligence, quantitative data integration, and professional prompt optimization

---

## 🤖 Multi-Agent Architecture Implementation (August 2025)

### Revolutionary Architecture Upgrade

The trading bot has been upgraded from a monolithic pipeline to a sophisticated multi-agent system based on the latest research in AI coordination and cognitive architecture. This upgrade addresses the key challenges identified in modern multi-agent literature.

**Key Principles Implemented:**
- **Centralized Orchestration**: The Supervisor-AI ensures shared context and prevents agent fragmentation
- **Cognitive Transparency**: Every agent logs its complete thought process for audit and debugging
- **Specialized Intelligence**: Each agent focuses on a specific cognitive task with deep expertise
- **Robust Error Handling**: Individual agent failures don't crash the entire system
- **Context Preservation**: All agents operate with shared context to maintain coherent decision-making

### Agent Specifications (Enhanced August 2025)

| Agent | Role | Cognitive Function | Input | Output |
|-------|------|-------------------|-------|--------|
| **CoinGecko-AI** | Market Data Specialist | Real-time price data, trending analysis, market metrics | Token IDs, trending preferences | Live market data with quality assessment |
| **Supervisor-AI** | Central Orchestrator | Pipeline management, final validation, trade approval | Initial cycle trigger | Complete execution results |
| **Analyst-AI** | Market Intelligence | News aggregation, sentiment analysis, CoinGecko data integration | Research directives + CoinGecko data | Enhanced intelligence report with quantitative context |
| **Strategist-AI** | Prompt Engineering | Multi-source context assembly, OpenAI 2025 optimization | Intelligence + CoinGecko + portfolio data | Institutional-grade AI prompt payload |
| **Trader-AI** | AI Execution | OpenAI API calls, response parsing, quality assessment | Enhanced prompt payload | Validated trading plan with confidence metrics |

### Communication Protocol

All inter-agent communication follows a standardized JSON format with complete audit trails and cognitive transparency logging.

### Cognitive Logging System

Each agent maintains complete cognitive transparency through timestamped transcript files in `logs/agent_transcripts/{YYYY-MM-DD}/`.

### Pipeline State Management (Enhanced August 2025)

The Supervisor-AI manages pipeline execution through well-defined states: IDLE → RUNNING_COINGECKO → RUNNING_ANALYST → RUNNING_STRATEGIST → RUNNING_TRADER → REVIEWING_PLAN → EXECUTING_TRADES → COMPLETED.

**Enhanced Pipeline Flow:**
1. **Stage 1:** CoinGecko-AI fetches real-time market data for 10 tracked cryptocurrencies
2. **Stage 2:** Analyst-AI aggregates news intelligence and integrates with CoinGecko data  
3. **Stage 3:** Strategist-AI builds institutional-grade prompts with multi-source intelligence
4. **Stage 4:** Trader-AI executes enhanced prompts and parses trading decisions
5. **Stage 5:** Supervisor-AI reviews and validates trading plans
6. **Stage 6:** Trade execution (if approved)
7. **Stage 7:** Performance tracking and cognitive logging

### Quality Assurance & Validation

The multi-agent system implements comprehensive quality controls at each stage with metrics for intelligence quality, strategy confidence, decision quality, and risk assessment.

### Deployment Instructions

**New Production Scheduler:**
```bash
python scheduler_multiagent.py
```

**Demo and Testing:**
```bash
python run_multiagent_demo.py
```

**Single Demo Run:**
```bash
python scheduler_multiagent.py demo
```

### Migration from Legacy System (Updated August 2025)

The enhanced multi-agent system provides significant improvements over the legacy monolithic architecture:

**Enhanced Capabilities:**
- **Real-Time Market Intelligence:** CoinGecko API integration provides live price data and trending analysis
- **Comprehensive News Coverage:** 57 crypto + 81 macro keywords capture institutional flows, ETF developments, Fed policy, and regulatory changes
- **Institutional-Grade AI Analysis:** OpenAI 2025 best practices with professional prompt optimization and quantitative data integration
- **Enhanced Cognitive Transparency:** Complete audit trails for all agent decisions and data flows
- **Multi-Source Intelligence:** Combines quantitative CoinGecko data with qualitative news analysis
- **Professional Output Quality:** Institutional morning briefing format with confidence levels and specific trading opportunities

**Backward Compatibility:**
- Legacy modules remain functional during transition
- Existing logs and data structures preserved
- Gradual migration path with parallel testing capabilities

**Performance Improvements:**
- Dramatically improved AI decision quality through specialized agents
- Better market context awareness with real-time data integration
- Enhanced risk assessment with macro/regulatory intelligence
- More actionable trading insights with institutional-grade analysis

---
