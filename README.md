# GPT-5 Kraken Trading Bot

An experimental, fully autonomous cryptocurrency trading bot that uses OpenAI's GPT-5 to manage a portfolio on the Kraken exchange.

**Disclaimer:** This is a highly experimental project and is for educational purposes only. It is NOT financial advice. Use at your own risk.

---

## 🧠 Core Concept

This bot runs on a daily schedule to perform the following cycle:
1.  **Fetch Data:** It connects to Kraken to get the current portfolio balance and live market prices.
2.  **Build Context:** It constructs a detailed prompt for ChatGPT, including current holdings, market data, and the bot's evolving investment thesis.
3.  **Get AI Strategy:** It sends the prompt to the GPT-5 API to get a new set of trading decisions (buy/sell/hold).
4.  **Execute Trades:** It parses the AI's response and executes the recommended trades on Kraken.
5.  **Log Everything:** It logs every trade, daily portfolio value, and the updated thesis to local CSV and Markdown files for performance tracking.

The primary objective is to test whether an AI can generate alpha against standard crypto benchmarks (BTC and ETH) over a fixed period.

## ⚙️ How It Works

```mermaid
graph TD
    A[Scheduler (Runs Daily)] --> B{Kraken API};
    B --> C[Fetch Balance & Prices];
    C --> D{Decision Engine};
    D --> E[Build Prompt for AI];
    E --> F{OpenAI API (GPT-5)};
    F --> G[Receive Trading Plan];
    G --> H{Parse AI Response};
    H --> I{Trade Executor};
    I --> J[Execute Trades via Kraken];
    J --> K[Log Results (Trades, Equity, Thesis)];
```

## 🚀 Getting Started

### Prerequisites
*   Python 3.11+
*   A Kraken account with API keys
*   An OpenAI account with an API key

### 1. Clone the Repository
```bash
git clone <repository-url>
cd chatgpt-kraken-bot
```

### 2. Set Up a Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a file named `.env` in the root of the project directory and add your API keys:
```env
KRAKEN_API_KEY="your_kraken_api_key"
KRAKEN_API_SECRET="your_kraken_secret_key"
OPENAI_API_KEY="your_openai_api_key"
```

## USAGE

### Running the Bot
The main entry point for the bot will be the `scheduler.py` script, which runs the trading logic on a daily schedule. (This is currently under development).

```bash
python scheduler.py
```

### Running Tests
To ensure all components are working correctly, you can run the unit tests:
```bash
python -m unittest discover Tests/
```
---

This project is tracked with a detailed technical document in `IMPLEMENTATION.md`.
