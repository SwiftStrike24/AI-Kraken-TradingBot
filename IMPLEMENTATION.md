
# ChatGPT-Kraken Portfolio Bot — Initial Implementation

## 🧠 Concept

A fully autonomous crypto trading bot powered by ChatGPT 4o.
It runs daily at 07:00 AM MST, evaluates the market, and rebalances a portfolio of Kraken-listed tokens with the goal of generating consistent alpha vs BTC and ETH.
The strategy is experimental, transparent, and performance-logged.

---

## 🗓️ Start Date

**July 30, 2025**
Initial balance: **\$100.00 USDC**

---

## ⚙️ Architecture Overview

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

```
chatgpt-kraken-bot/
├── bot/
│   ├── kraken_api.py
│   ├── decision_engine.py
│   ├── trade_executor.py
│   ├── performance_tracker.py
│   └── research_agent.py
├── Tests/
│   ├── test_kraken_api.py
│   ├── test_decision_engine.py
│   ├── test_trade_executor.py
│   ├── test_performance_tracker.py
│   └── test_research_agent.py
├── logs/
│   ├── trades.csv
│   ├── equity.csv
│   ├── thesis_log.md
│   ├── daily_research_report.md
│   └── research_cache.json
├── .env
├── requirements.txt
├── scheduler.py
├── README.md
└── implementation.md
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
| `bot/decision_engine.py`   | ✅ Complete | Enhanced to accept and integrate market research reports into AI prompts.                     |
| `Tests/test_decision_engine.py` | ⚠️ Needs Update | Needs updates to test new research report integration.         |
| `bot/trade_executor.py`    | ✅ Complete | Executes AI's trade plan using a safe, two-phase (validate-then-execute) process. |
| `Tests/test_trade_executor.py` | ✅ Complete | Verifies that trade validation, execution, and error handling work correctly.       |
| `bot/performance_tracker.py`| ✅ Complete | Uses robust asset pair validation for accurate equity calculations.               |
| `Tests/test_performance_tracker.py` | ⚠️ Needs Update | Needs updates to test new asset pair handling logic.             |
| `bot/research_agent.py`    | ✅ Complete | New module that gathers market intelligence from RSS feeds and web sources.        |
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

### AI Research Agent Integration (August 2025)
- **Problem Solved:** Decision engine was operating in a "portfolio vacuum" without real-world market context
- **Solution:** Added comprehensive research agent that gathers market intelligence before each trading decision
- **Features:**
  - RSS feed aggregation from major crypto news sources (CoinDesk, CoinTelegraph, The Block, etc.)
  - Macroeconomic and regulatory news filtering
  - Intelligent keyword-based content filtering
  - Caching system to prevent duplicate processing
  - Robust error handling with graceful degradation
  - Daily research reports saved for audit trail
- **Benefits:** AI now makes trading decisions with awareness of current market events, regulatory changes, and sentiment

### Market Intelligence Pipeline
- **Stable Data Sources:** Prioritizes RSS feeds over web scraping for reliability
- **Smart Filtering:** Uses crypto and macro keyword filtering to surface relevant content
- **Rate Limiting:** Respectful request timing to avoid IP blocks
- **Error Resilience:** Individual source failures don't crash the entire research process
- **Structured Output:** Generates clean, markdown-formatted reports for AI consumption

---

##
