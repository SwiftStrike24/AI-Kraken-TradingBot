
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
| `bot/kraken_api.py`        | ✅ Complete | Fully implemented and unit-tested. Handles auth, rate limits, and required endpoints. |
| `Tests/test_kraken_api.py` | ✅ Complete | Provides comprehensive test coverage for the Kraken API module using mocks.           |
| `bot/decision_engine.py`   | ✅ Complete | Queries OpenAI with context to get a JSON-formatted trading plan.                     |
| `Tests/test_decision_engine.py` | ✅ Complete | Mocks external services to validate prompt generation and response parsing.         |
| `bot/trade_executor.py`    | ✅ Complete | Executes AI's trade plan using a safe, two-phase (validate-then-execute) process. |
| `Tests/test_trade_executor.py` | ✅ Complete | Verifies that trade validation, execution, and error handling work correctly.       |
| `bot/performance_tracker.py`| ✅ Complete | Logs trades, daily equity, and AI thesis to CSV and Markdown files.               |
| `Tests/test_performance_tracker.py` | ✅ Complete | Verifies logging logic for equity, trades, and thesis without file I/O.             |
| `scheduler.py`             | ✅ Complete | Orchestrates the daily trading cycle and manages the schedule.                      |

---

##
