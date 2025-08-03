
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
   └── Kraken API → Get balance + token prices
       └── Build ChatGPT prompt
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
├── Tests/
│   ├── test_kraken_api.py
├── logs/
│   ├── trades.csv
│   ├── equity.csv
│   └── thesis_log.md
├── .env
├── requirements.txt
├── scheduler.py
├── README.md
└── implementation.md
```

---

## 📌 Execution Cycle

* Runs: **7 days/week at 7:00 AM MST**
* Decision engine builds ChatGPT prompt using:

  * Current holdings
  * Current price data
  * Thesis summary
* OpenAI returns portfolio actions
* Trades executed on Kraken
* Logs updated with:

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
| `bot/decision_engine.py`   | ✅ Complete | Uses robust asset pair validation to avoid "Unknown asset pair" errors.                     |
| `Tests/test_decision_engine.py` | ⚠️ Needs Update | Needs updates to mock new KrakenAPI methods.         |
| `bot/trade_executor.py`    | ✅ Complete | Executes AI's trade plan using a safe, two-phase (validate-then-execute) process. |
| `Tests/test_trade_executor.py` | ✅ Complete | Verifies that trade validation, execution, and error handling work correctly.       |
| `bot/performance_tracker.py`| ✅ Complete | Uses robust asset pair validation for accurate equity calculations.               |
| `Tests/test_performance_tracker.py` | ⚠️ Needs Update | Needs updates to test new asset pair handling logic.             |
| `scheduler.py`             | ✅ Complete | Loads environment variables early before any imports for robust configuration.                      |

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

---

##
