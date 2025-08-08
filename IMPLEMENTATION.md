# ChatGPT-Kraken Portfolio Bot — Initial Implementation

## 🧠 Concept

A fully autonomous crypto trading bot powered by OpenAI GPT‑5 with institutional-grade market intelligence.
It runs daily at 07:00 AM MST, evaluates the market using real-time data and comprehensive news analysis, and rebalances a portfolio of Kraken-listed tokens with the goal of generating consistent alpha vs BTC and ETH.
The strategy is experimental, transparent, and performance-logged.

## ⚡ Latest Enhancements (August 2025)

**🚀 MODEL UPGRADE (August 7, 2025): GPT‑5 Migration & Safe Fallback — IMPLEMENTED ✅**
- Default model changed from `gpt-4o` to `gpt-5-2025-08-07` across all OpenAI calls.
- Introduced centralized model config helper `bot/openai_config.py` with env overrides:
  - `OPENAI_DEFAULT_MODEL` (default `gpt-5-2025-08-07`)
  - `OPENAI_FALLBACK_MODEL` (default `gpt-4o`)
- Added `build_chat_completion_params()` to automatically use `max_completion_tokens` for GPT‑5 and `max_tokens` for older models.
- Trader-AI now uses a guarded call with automatic fallback to the fallback model on API error or JSON parse failure (response_format json_object enforced).
- ResearchAgent retries once with the fallback model on API error.
- Removed hardcoded `max_tokens` limits from OpenAI calls to allow for maximum length responses.
- Added richer logs: model selected, finish_reason, token usage, and JSON-parse success/failure for visibility.
- Files Modified:
  - `agents/trader_agent.py` (fallback wrapper + model resolution + usage logs + GPT‑5 param handling)
  - `bot/research_agent.py` (env-backed model + one-shot fallback + GPT‑5 param handling)
  - `bot/prompt_engine.py` (default model resolution via helper)
  - `README.md` (GPT‑5 now primary)
  - NEW: `bot/openai_config.py`
- Impact: Seamless migration to GPT‑5 with safe fallback to GPT‑4o if account/availability issues occur. Zero changes to trading logic or formats.
- Status: ✅ PRODUCTION READY

**🧠 REFLECTIVE INTELLIGENCE UPGRADE (August 11, 2025):** Historical Context & Self-Correction - IMPLEMENTED ✅
- Problem Solved: 413 Request Entity Too Large from OpenAI due to oversized prompts (long cognitive transcripts + verbose context).
- Root Cause: `<COGNITIVE_HISTORY>` injected raw transcripts; no holistic prompt-size budgeting across sections.
- Technical Solution:
  - Reflection via Gemini 2.5 Pro: `ReflectionAgent` now uses `gemini-2.5-pro` (1M context) to analyze long history and produce a compact JSON reflection. See `bot/gemini_client.py` and `bot/reflection_prompt_template.md`.
  - Lean Downstream Context: Removed `<COGNITIVE_HISTORY>` from `bot/prompt_template.md`. Only the compact `historical_reflection` text is passed to `gpt-4o`.
  - Preflight Size Logs: Added prompt-size logging (chars, est tokens) in `PromptEngine` and `TraderAgent` before API calls.
- Files Modified / Added:
  - `agents/reflection_agent.py` (Gemini integration, bounded transcripts, compact output)
  - `bot/gemini_client.py` (NEW)
  - `bot/reflection_prompt_template.md` (NEW)
  - `bot/prompt_template.md` (removed `<COGNITIVE_HISTORY>`)
  - `bot/prompt_engine.py` (removed `cognitive_history` arg; added size logs)
  - `agents/strategist_agent.py` (stopped passing `cognitive_history`)
  - `requirements.txt` (added `google-generativeai`)
- Impact: Eliminates prompt bloat to OpenAI, while upgrading reflection quality via Gemini's 1M-token context. Trader prompts are leaner and more reliable.
- Config: Set `GEMINI_API_KEY` env. Optional overrides: `GEMINI_REFLECTION_MODEL`, `GEMINI_TEMPERATURE`, `GEMINI_TOP_P`, `GEMINI_MAX_OUTPUT_TOKENS`.
- Status: ✅ PRODUCTION READY

**🧩 REFLECTION CONTEXT EXPANSION (August 12, 2025) — IMPLEMENTED ✅**
- Problem: Reflection-AI lacked the raw data context needed for accurate self-diagnosis and execution guardrails.
- Solution: Enriched `ReflectionAgent` inputs with bounded raw snippets of equity, trades, and the latest daily research, with size-aware preflight and caching.
- Details:
  - Template (`bot/reflection_prompt_template.md`) now includes:
    - `{equity_raw_block}`: last N rows from `logs/equity.csv`
    - `{trades_raw_block}`: last N rows from `logs/trades.csv`
    - `{latest_research_block}`: tail-truncated `logs/daily_research_report.md`
  - ReflectionAgent additions:
    - Env toggles: `REFLECTION_INCLUDE_EQUITY_RAW=1`, `REFLECTION_INCLUDE_TRADES_RAW=1`, `REFLECTION_INCLUDE_RESEARCH_REPORT=1`
    - Size controls: `REFLECTION_MAX_CSV_ROWS=200`, `REFLECTION_MAX_RESEARCH_CHARS=5000`
    - Token budgeting: warn at `REFLECTION_WARN_TOKENS` (default 24k), clamp at `REFLECTION_CLAMP_TOKENS` (default 50k) by halving CSV rows and research chars
    - Provenance logs: rows included, time ranges, research mtime/Generated header, per-block token counts, total tokens
    - Cache key extended to include SHA256 of raw blocks to prevent stale reuse
    - Optional freshness: supervisor may pass `latest_research_override` (in-memory report) to bypass file staleness
- Impact: GPT‑5 receives ground-truth raw context alongside summaries, improving accuracy of patterns/guardrails and reducing hallucinations about execution issues.
- Files Changed:
  - `agents/reflection_agent.py`
  - `bot/reflection_prompt_template.md`
- Status: ✅ PRODUCTION READY

**📈 P&L TRACKER (August 12, 2025) — IMPLEMENTED ✅**
- Objective: Provide daily P&L metrics for monitoring and to feed concise summaries into agents.
- Implementation (`bot/performance_tracker.py`):
  - New CSV: `logs/pnl.csv` with columns `date,timestamp,total_equity_usd,daily_return_pct,rolling_vol_7d,rolling_sharpe_30d,drawdown_pct,max_drawdown_pct`
  - New methods:
    - `log_daily_pnl()`: builds daily series from `equity.csv`, computes returns/vol/sharpe/drawdowns
    - `get_pnl_summary(days=3) -> str`: quick textual summary for reflection/strategist
  - UTC-safe timestamps, robust type coercion, and graceful fallbacks
- Usage: call after equity logging or at end-of-run summary step
- Status: ✅ PRODUCTION READY

---

## 🗓️ Start Date

**July 30, 2025**
Initial balance: **$100.00 USDC**

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

### New Multi-Agent Architecture (August 2025+) - **DEPRECATED**
This static pipeline view is now deprecated in favor of the dynamic loop below.
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

### 🧠 New **Autonomous** Multi-Agent Architecture (August 7, 2025+)
The system now operates as a persistent agent with two interconnected loops: a high-frequency, lightweight **monitoring loop** and a deep, event-triggered **decision-making loop**.

```mermaid
graph TD
    subgraph "Scheduler (Continuous Loop - every 1 min)"
        A[Start] --> B{Supervisor.monitor_market()};
        B --> C{Price > 5% change?};
        B --> D{Breaking News?};
        B --> E{07:00 MST?};
        C -- Yes --> F[Trigger Full Cycle];
        D -- Yes --> F;
        E -- Yes --> F;
        C -- No --> G[Wait 1 min];
        D -- No --> G;
        E -- No --> G;
        G --> A;
    end

    subgraph "Full Trading Cycle (Triggered by Scheduler or Anomaly)"
        H[Start Cycle] --> I{Supervisor: Run PerformanceAnalyst};
        I --> J[Get Feedback on Last Trades];
        J --> K{Supervisor: Run CoinGecko + Analyst Agents};
        K --> L[Get Market Data & News];
        L --> M{Supervisor: Run Strategist};
        M --> N[Build Prompt with Performance Feedback];
        N --> O{Supervisor: Run Trader};
        O --> P[Generate Trading Plan];
        P --> Q{Supervisor: Review Plan};
        Q -- Plan Rejected --> K;
        Q -- Plan Approved --> R[Execute Trades];
    end
    
    F --> H;
```

### ✨ **Reflective** Multi-Agent Architecture (August 11, 2025+)
The latest architecture introduces a `ReflectionAgent` that runs at the start of the full cycle, endowing the system with long-term memory.

```mermaid
graph TD
    subgraph "Full Trading Cycle (Now with Reflection)"
        H[Start Cycle] --> R_A{Supervisor: Run ReflectionAgent};
        R_A --> I[Get Historical Performance & Learnings];
        I --> J{Supervisor: Run PerformanceAnalyst};
        J --> K[Get Feedback on Last Trades];
        K --> L{Supervisor: Run CoinGecko + Analyst Agents};
        L --> M[Get Market Data & News];
        M --> N{Supervisor: Run Strategist};
        N --> O[Build Prompt with Reflection, Performance, and Market Data];
        O --> P{Supervisor: Run Trader};
        P --> Q[Generate Trading Plan];
        Q --> S{Supervisor: Review Plan};
        S -- Plan Rejected --> L;
        S -- Plan Approved --> T[Execute Trades];
    end
```

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
│   ├── trader_agent.py          # AI execution specialist
│   └── reflection_agent.py      # 🆕 Self-reflection and historical analysis
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

The bot now operates as a **persistent, autonomous agent** with two modes:

1.  **Continuous Monitoring Mode (Default):**
    *   Runs: **Continuously, every 60 seconds.**
    *   Action: Performs lightweight checks on currently held assets and scans for high-impact news.
    *   Goal: Detect market anomalies (volatility spikes, breaking news) that require immediate attention.

2.  **Full Trading Cycle Mode (Triggered):**
    *   Runs: **On a schedule (7:00 AM MST) OR when triggered by the monitoring loop.**
    *   **Step 1: Performance Review:** The `StrategistAgent` first analyzes the PnL of the last trade cycle.
    *   **Step 2: Intelligence Gathering:** The `AnalystAgent` gathers comprehensive market intelligence.
    *   **Step 3: Strategy Formulation:** The `StrategistAgent` builds a prompt including the **new performance review**, market data, and portfolio context.
    *   **Step 4: AI Decision:** The `TraderAgent` queries the AI to generate a new trading plan.
    *   **Step 5: Supervisor Review & Refinement:** The `SupervisorAgent` validates the plan. If the plan is low-quality, it can loop back and delegate new research tasks to refine the strategy.
    *   **Step 6: Execution & Logging:** Approved trades are executed, and all data (trades, equity, thesis, performance) is logged.

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

### Critical Bug Fix: Supervisor Validation Logic (August 4, 2025) - RESOLVED ✅
- **Problem Solved:** Supervisor-AI was incorrectly rejecting valid trading plans with empty trades lists `[]` 
- **Root Cause:** Validation logic used `if not trading_plan.get("trades")` which treats empty lists as falsy
- **Solution:** Changed to `if "trades" not in trading_plan` to properly check for key existence
- **Impact:** Trading plans with no trades (hold strategies) now correctly pass validation
- **Status:** ✅ PRODUCTION READY - All pipeline stages working correctly

### Critical Bug Fix: CSV Parsing Error in Performance Feedback (August 4, 2025) - RESOLVED ✅
- **Problem Solved:** Strategist-AI was failing to read performance history due to `KeyError: 'total_equity_usd'`
- **Root Cause:** `equity.csv` file saved without headers, but code assumed headers existed when using `pd.read_csv()`
- **Solution:** Added `names=['timestamp', 'total_equity_usd']` parameter to explicitly define column names
- **Files Fixed:** 
  - `agents/strategist_agent.py` - Performance context gathering method
  - `scheduler_multiagent.py` - Interactive equity status check ([L] command)
- **Impact:** AI now receives complete performance history for informed decision-making
- **Status:** ✅ PRODUCTION READY - Performance feedback loop fully operational

### Small Portfolio Trading Logic Enhancement (August 4, 2025) - IMPLEMENTED ✅
- **Problem Solved:** AI was overly conservative with small portfolios, refusing to trade with $10.74 balance
- **Root Cause:** AI considered small positions "insignificant" and worried about minimum order sizes
- **Solution:** Added "SMALL PORTFOLIO MANDATE" to prompt template - prioritize ANY crypto position over 100% cash for portfolios under $50
- **File Modified:** `bot/prompt_template.md` - Added constraint #4 for small portfolio guidance
- **Impact:** AI now understands that small positions can generate meaningful alpha vs. holding cash
- **Status:** ✅ PRODUCTION READY - AI will now trade with small capital amounts

### Market Intelligence Token Limit Removal (August 4, 2025) - IMPLEMENTED ✅
- **Problem Solved:** Strategist-AI was truncating research reports at 3000 tokens, limiting market context
- **Root Cause:** Hardcoded `max_tokens=3000` in `PromptEngine` constructor was cutting off valuable intelligence
- **Solution:** Removed token limit entirely - changed default from 3000 to `None` (no limit)
- **Files Modified:** 
  - `bot/prompt_engine.py` - Removed 3000-token constraint, added None check
  - `Tests/test_prompt_engine.py` - Updated test expectations for no-limit default
- **Impact:** AI now receives complete market intelligence without artificial truncation
- **Status:** ✅ PRODUCTION READY - Full context passing to trading decisions

### Multi-Strategy & Risk Allocation Framework (August 4, 2025) - IMPLEMENTED ✅
- **Problem Solved:** AI made basic decisions with insufficient risk management and strategy selection
- **Root Cause:** Single-strategy approach with fixed position sizing led to "insufficient funds" errors and suboptimal allocation
- **Solution:** Comprehensive upgrade to percentage-based allocation with multi-strategy framework
- **Files Modified:**
  - `bot/prompt_template.md` - Added TRADING_STRATEGIES and RISK_ALLOCATION_ENGINE sections
  - `bot/trade_executor.py` - Implemented percentage-to-volume conversion with portfolio value calculation
  - `agents/supervisor_agent.py` - Added confidence-based validation and allocation limits
  - `agents/analyst_agent.py` - Added volatility metrics and market regime detection
- **Key Features:**
  - **Percentage-Based Allocation:** Trades specified as % of portfolio (e.g., 25%) instead of fixed volume
  - **Multi-Strategy Selection:** MOMENTUM_TRADING, MEAN_REVERSION, ALTCOIN_ROTATION, DEFENSIVE_HOLDING
  - **Confidence-Based Sizing:** High confidence = larger allocation, low confidence = smaller allocation
  - **Dynamic Risk Management:** Supervisor validates confidence-allocation alignment
  - **Market Regime Detection:** AI receives volatility metrics and strategy recommendations
- **Impact:** Eliminates "insufficient funds" errors, enables intelligent risk scaling, provides strategic flexibility
- **Status:** ✅ PRODUCTION READY - Advanced multi-strategy trading with professional risk management

### Format Validation Bug Fix (August 4, 2025) - RESOLVED ✅
- **Problem Solved:** Trader-AI validation error "missing required field 'volume'" when using new percentage format
- **Root Cause:** `_validate_single_trade` method still expected legacy volume format instead of new allocation_percentage format
- **Solution:** Updated validation logic to handle both percentage-based and legacy volume-based trade formats
- **File Modified:** `agents/trader_agent.py` - Enhanced validation to support dual format compatibility
- **Impact:** AI can now properly validate percentage-based trades with confidence scores and reasoning
- **Status:** ✅ PRODUCTION READY - Full percentage-based trading validation working

### Kraken Pair Mapping Bug Fix (August 4, 2025) - RESOLVED ✅
- **Problem Solved:** "Cannot get price for pair: ETHUSD" error - AI was using simplified pair names but Kraken uses complex naming
- **Root Cause:** `_normalize_pair` method couldn't map "ETHUSD" to actual Kraken pair name "XETHZUSD"
- **Solution:** Enhanced pair normalization to use Kraken's `asset_to_usd_pair_map` for accurate mapping
- **File Modified:** `bot/trade_executor.py` - Completely rewritten `_normalize_pair` method with intelligent mapping
- **Enhanced Features:**
  - Direct asset-to-pair mapping lookup using Kraken's internal mapping
  - Fallback logic for common prefixes (X, Z)
  - Detailed error logging with similar pair suggestions
  - Better variable naming and error handling
- **Impact:** AI can now successfully convert percentage allocations to actual trades with correct Kraken pair names
- **Status:** ✅ PRODUCTION READY - Robust pair name resolution for all supported assets

### Trading Pair and Volume Validation Fixes (August 4, 2025) - IMPLEMENTED ✅
- **Problem Solved:** AI was suggesting invalid Kraken pair names (e.g., 'ETHUSD' instead of 'XETHZUSD') and trades below minimum order sizes
- **Root Cause:** AI lacked knowledge of exact Kraken pair names and minimum order volumes, causing API validation failures
- **Solution:** Comprehensive multi-layer approach with AI guidance and hard guardrails
- **Files Enhanced:**
  - **KrakenAPI:** Added `get_pair_details()` and `get_all_usd_trading_rules()` methods to expose ordermin data
  - **Prompt Template:** Added `<TRADING_RULES>` section with valid Kraken pairs and minimum order sizes
  - **Strategist-AI:** Added `_gather_trading_rules()` method to format trading constraints for AI consumption
  - **PromptEngine:** Updated `build_prompt()` to inject trading rules into AI context
  - **TradeExecutor:** Added pre-validation minimum volume checks to prevent API errors
  - **PerformanceTracker:** Added `log_rejected_trade()` method for audit transparency
  - **Supervisor-AI:** Integrated rejected trade logging for complete audit trail
- **Key Improvements:**
  - **AI Guidance:** AI now receives exact Kraken pair names (e.g., 'XETHZUSD', 'XXBTZUSD') and minimum order sizes
  - **Pre-flight Validation:** Volume checks before API calls prevent "volume minimum not met" errors
  - **Graceful Degradation:** Individual trade failures don't abort entire trading cycle
  - **Audit Transparency:** All rejected trades logged to `logs/rejected_trades.csv` with reasoning
  - **Robust Error Handling:** System continues with valid trades when some fail validation
- **Impact:** Eliminates trading cycle crashes, ensures only valid trades reach Kraken API, improves AI decision quality
- **Status:** ✅ PRODUCTION READY - Comprehensive trading validation and error prevention

### Allocation Percentage Validation Fix (August 4, 2025) - IMPLEMENTED ✅
- **Problem Solved:** Error "Trade 0: invalid allocation_percentage format '0.95'" when AI returned 95% allocation for small portfolios
- **Root Cause:** Trader-AI validation logic limited all portfolios to 40% max allocation, conflicting with small portfolio mandate to avoid holding excessive cash
- **Solution:** Portfolio-size-aware validation with flexible allocation limits
- **Files Modified:**
  - **Trader-AI:** Updated `_validate_trade_format()` to allow up to 95% allocation for portfolios <$50
  - **Supervisor-AI:** Updated `_validate_trading_plan()` and added `_get_portfolio_value()` for consistent validation
  - **Prompt Template:** Clarified position sizing rules with separate limits for small vs large portfolios
- **Key Changes:**
  - **Small Portfolios (<$50):** Allow up to 95% allocation per position to maximize crypto exposure
  - **Large Portfolios (>$50):** Maintain 40% max position size with 5% cash buffer
  - **Enhanced Error Messages:** Clear differentiation between format errors and range validation errors
  - **Conflict Resolution:** Resolved contradiction between 40% limit and small portfolio mandate
  - **Consistent Validation:** Both Trader-AI and Supervisor-AI now use same portfolio-size-aware logic
- **Impact:** Small portfolios ($10.53) can now execute meaningful trades without holding excessive cash
- **Status:** ✅ PRODUCTION READY - Tested and verified working with 95% allocation scenarios, end-to-end validation confirmed

### USD Trading Configuration Verification (August 4, 2025) - CONFIRMED ✅
- **Verification:** Confirmed bot correctly uses USD (not USDC) for all trading operations
- **Asset Mapping:** All cryptocurrencies map to USD trading pairs (e.g., SOL → SOLUSD, BTC → XBTZUSD)
- **Performance Tracking:** Equity calculations properly handle USD as base currency
- **Cash Handling:** USD balances treated as $1.00 per unit for equity calculations
- **Test Coverage:** Created comprehensive live trading test (`Tests/test_usd_trading_live.py`)
- **Status:** ✅ CONFIRMED READY - Bot will trade with your USD balance on Kraken

### Live Trading Test Fixes (August 4, 2025) - RESOLVED ✅
- **Problem Solved:** Multiple issues in live trading test preventing successful execution
- **Issues Fixed:**
  - **Minimum Order Size:** Kraken requires larger order volumes - increased test amount from $1 to $5
  - **Deprecated Datetime:** Fixed Python 3.12+ compatibility with timezone-aware datetime objects
  - **CSV Column Mismatch:** Fixed equity.csv reading to handle missing headers properly
  - **Success Detection Logic:** Fixed test to properly detect successful trade execution
- **Live Test Results:** Successfully executed real $5 SOL purchase (Transaction ID: OGR4IZ-OOBGP-BN5LKH)
- **Status:** ✅ FULLY OPERATIONAL - Live USD trading confirmed working on Kraken

### Trade Logging System Verification (August 4, 2025) - CONFIRMED ✅
- **Problem Addressed:** Ensuring all executed trades are properly logged to `logs/trades.csv`
- **Implementation:** Performance tracker automatically logs successful trades with full details
- **Trade Log Format:** CSV with columns: timestamp, pair, action, volume, txid
- **Integration Points:**
  - **Supervisor Agent:** Automatically logs all successful trades during pipeline execution
  - **Live Testing:** Manual logging in test scripts for verification
  - **Trade Executor:** Returns detailed trade results for logging
- **Verified Trades Logged:**
  - `OGR4IZ-OOBGP-BN5LKH`: 0.0296 SOL bought for ~$5.00 USD
  - `OYF53B-5HDPH-MUTK5N`: 0.0296 SOL bought for ~$5.00 USD
- **Status:** ✅ FULLY OPERATIONAL - All trades properly logged to CSV

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
| **Reflection-AI** | Historical Analyst | Analyzes past performance, logs, and cognitive transcripts | Historical log data | Actionable "Reflection Report" summarizing learnings |

### Communication Protocol

All inter-agent communication follows a standardized JSON format with complete audit trails and cognitive transparency logging.

### Cognitive Logging System

Each agent maintains complete cognitive transparency through timestamped transcript files in `logs/agent_transcripts/{YYYY-MM-DD}/`.

### Pipeline State Management (Enhanced August 2025)

The Supervisor-AI manages pipeline execution through well-defined states: IDLE → RUNNING_COINGECKO → RUNNING_ANALYST → RUNNING_STRATEGIST → RUNNING_TRADER → REVIEWING_PLAN → EXECUTING_TRADES → COMPLETED.

**Enhanced Pipeline Flow:**
1.  **(NEW) Stage 0: Performance Analysis:** Strategist-AI analyzes the PnL of the previous trade cycle.
2.  **Stage 1:** CoinGecko-AI fetches real-time market data for 10 tracked cryptocurrencies
3.  **Stage 2:** Analyst-AI aggregates news intelligence and integrates with CoinGecko data  
4.  **Stage 3:** Strategist-AI builds institutional-grade prompts with multi-source intelligence, **including the new performance analysis**.
5.  **Stage 4:** Trader-AI executes enhanced prompts and parses trading decisions
6.  **Stage 5:** Supervisor-AI reviews and validates trading plans
7.  **(NEW) Stage 5a - Refinement Loop:** If the plan is low-quality, the Supervisor can delegate new, targeted research tasks to the `Analyst-AI` and re-run the strategy formulation stages up to `max_refinement_loops` times.
8.  **Stage 6:** Trade execution (if approved)
9.  **Stage 7:** Performance tracking and cognitive logging

### Reflective Pipeline Flow (August 11, 2025+)
1.  **(NEW) Stage 0: Reflection:** `ReflectionAgent` analyzes all historical data (trades, equity, theses, transcripts) and produces a "Reflection Report".
2.  **Stage 1: Performance Analysis:** `StrategistAgent` analyzes the PnL of the *most recent* trade cycle.
3.  **Stage 2: Intelligence Gathering:** `CoinGeckoAgent` and `AnalystAgent` gather real-time market data and news.
4.  **Stage 3: Strategy Formulation:** `StrategistAgent` builds a prompt including the **new Reflection Report**, performance review, and live market data.
5.  **Stage 4: AI Decision:** `TraderAgent` queries the AI, which now has both long-term and short-term context.
6.  **Stage 5: Supervisor Review & Refinement:** The `SupervisorAgent` validates the plan, potentially looping back for revisions.
7.  **Stage 6: Execution & Logging:** Approved trades are executed.

### Quality Assurance & Validation

The multi-agent system implements comprehensive quality controls at each stage with metrics for intelligence quality, strategy confidence, decision quality, and risk assessment. The new Supervisor loop uses these metrics to decide whether to proceed or to seek more information.

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

### Interactive Scheduler Enhancement (August 4, 2025) - IMPLEMENTED ✅
- **Feature Added:** Real-time interactive controls for manual trading trigger and system monitoring
- **Keyboard Controls:**
  - **[ENTER]** - Instantly trigger trading cycle (bypasses 07:00 MST schedule)
  - **[S]** - Display current system status and next scheduled run
  - **[L]** - Show last portfolio equity and timestamp
  - **[T]** - Display recent trades with transaction IDs
  - **[Ctrl+C]** - Gracefully stop scheduler
- **Implementation:** Windows-compatible threading for non-blocking input handling
- **Benefits:** 
  - Test trading logic anytime without waiting for schedule
  - Monitor system status and performance in real-time
  - Instant access to portfolio and trade history
  - Professional operational interface for live trading
- **Status:** ✅ FULLY OPERATIONAL - Enhanced user experience with live controls

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

### System Message Separation Fix (August 4, 2025) - IMPLEMENTED ✅
- **Problem Solved:** OpenAI interface showing "Add system instructions to optimize" because system instructions were embedded in user content instead of proper system messages
- **Root Cause:** `PromptEngine.build_openai_request()` was sending all content as a single user message, including `<SYSTEM_INSTRUCTIONS>` tags within user content
- **Solution:** Implemented proper system/user message separation following OpenAI best practices
- **Files Modified:**
  - **bot/prompt_engine.py**: Updated `build_openai_request()` method to extract system instructions and create proper message structure
  - Added `_extract_system_instructions()` method to parse and separate system content from user content using regex
- **Technical Implementation:**
  - **Before**: `messages: [{"role": "user", "content": "<SYSTEM_INSTRUCTIONS>..."}]`
  - **After**: `messages: [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]`
  - Uses regex to extract content between `<SYSTEM_INSTRUCTIONS>` tags
  - Removes system instruction tags from user content to create clean separation
  - Maintains fallback system message if no system instructions found in template
- **Benefits:**
  - ✅ **OpenAI Best Practices**: Follows proper system/user message structure for optimal AI performance
  - ✅ **Token Efficiency**: System messages are processed more efficiently than user instructions
  - ✅ **Behavioral Consistency**: System messages provide stronger behavioral guardrails
  - ✅ **Clean Interface**: OpenAI playground will no longer show optimization suggestions
- **Impact:** AI responses will be more consistent and follow instructions more reliably due to proper message role separation
- **Status:** ✅ PRODUCTION READY - Prompt engine now creates proper OpenAI message structure automatically

## 🔧 Agent API Structure Fixes (August 2025)

**Issue Resolved:** Multiple agents were embedding system instructions in user messages instead of using proper OpenAI message structure

**Agents Fixed:**
- **agents/trader_agent.py**: Now properly extracts system instructions from prompts and creates structured messages
- **bot/decision_engine.py**: Updated to use PromptEngine's `build_openai_request()` method for proper message structure

**Technical Changes:**
- **trader_agent.py**: Added system instruction extraction logic and proper message array construction
- **decision_engine.py**: Replaced manual prompt building with PromptEngine's structured request method
- Both agents now follow the same pattern: system instructions in system role, context in user role

**Result:** All OpenAI API calls now use proper system/user message separation for optimal AI performance

---

## 🛡️ Error Handling & Resilience (August 2025)

**Objective:** Enhance system observability and ensure the pipeline can gracefully handle partial failures without crashing the entire trading cycle.

**Key Enhancements:**

### 1. **🎨 Enhanced Observability with Rich Logging**
- **Colorful Terminal Output:** Implemented `rich` library for colored logging (`INFO`, `WARNING`, `ERROR`, `CRITICAL`) to make terminal output intuitive and easy to parse.
- **Emoji-Enhanced Logs:** Added emojis (`✅`, `⚠️`, `❌`, `🔥`) to log levels for quick visual identification of message severity.
- **Improved Readability:** Standardized log formats across all modules for a clean, professional interface.
- **Files Modified:**
  - `bot/logger.py`: **NEW** central logging configuration module.
  - `scheduler_multiagent.py`: Integrated new logger and end-of-run summary.
  - All `agents/*.py` and `bot/*.py` files updated to use the new centralized logger.

### 2. **🤖 Agent Fallback System in Supervisor-AI**
- **Resilient Execution Wrapper:** Implemented a new `_execute_with_fallback` method in `Supervisor-AI` to wrap agent calls in a `try...except` block, preventing single-agent failures from crashing the pipeline.
- **Defined Fallback Strategies:**
  - **`CoinGecko-AI` / `Analyst-AI` Failure:** System logs a `WARNING`, proceeds in a "degraded" state with incomplete data, and notifies the user in the end-of-run summary.
  - **`Strategist-AI` Failure:** Treated as a `CRITICAL` error that aborts the trading portion of the cycle to prevent uninformed decisions.
  - **`Trader-AI` Failure:** Falls back to a safe `DEFENSIVE_HOLDING` strategy (no trades) to protect capital.
- **Degraded Mode Reporting:** The end-of-run summary now clearly indicates if any agent failed and a fallback was used, marking the run as **"✅ Completed with degraded functionality."**
- **Files Modified:**
  - `agents/supervisor_agent.py`: Added `_execute_with_fallback` and specific fallback logic for each agent.

### 3. **📊 End-of-Run Summary**
- **Mission Control Overview:** At the end of each run, `Supervisor-AI` presents a clean, formatted summary of any warnings or critical errors encountered during the cycle.
- **Instant Health Check:** Provides a quick, scannable overview of the trading cycle's health, highlighting issues like failed news feeds or dust positions.
- **Example Summary:**
  ```
  ⚠️ WARNINGS:
    - CoinGecko-AI failed, proceeding with no market data
    - Analyst-AI failed, proceeding with no news data
  ```

**Benefits:**
- ✅ **Improved Debugging:** Rich, colored logs make it easier to spot issues and trace errors.
- ✅ **Enhanced Resilience:** The bot can now survive partial failures and default to a safe state.
- ✅ **Better Observability:** The end-of-run summary provides an instant health check of the trading cycle.
- ✅ **Production-Ready:** These enhancements move the bot closer to a robust, self-healing system suitable for live deployment.

---

### 🐞 Critical Bug Fix: Trade Validation Logic (August 2025) - RESOLVED ✅
- **Problem Solved:** `TradeExecutor` was failing to validate `sell` orders, incorrectly reporting "Insufficient balance" even when funds were available.
- **Root Cause:** The logic to identify the asset being sold (e.g., `XRP` from `XXRPZUSD`) was flawed. It used simple string manipulation (`.replace('USD', '')`), which failed on complex official pair names.
- **Solution:** Rewritten the asset extraction logic in `_validate_trade_against_holdings` to use `kraken_api.get_pair_details()`. This method reliably fetches the official `base` asset for any given pair, ensuring balance checks are always performed against the correct holding.
- **Impact:** Sell order validation is now accurate and reliable, preventing erroneous trade rejections and improving overall trading robustness.
- **Status:** ✅ PRODUCTION READY - Trade validation logic is now resilient to complex pair names.

---

### 💸 "Insufficient Funds" Error & Small Portfolio Logic (August 2025) - RESOLVED ✅
- **Problem Solved:** The bot was failing with "EOrder:Insufficient funds" errors when trying to execute `buy` orders, even after `sell` orders should have freed up enough cash. Additionally, the AI was attempting to over-diversify the small $10 portfolio, resulting in trades too small to meet Kraken's minimum order sizes.
- **Root Cause:**
  1. **Execution Order:** The `TradeExecutor` validated all trades at once, failing `buy` orders because it didn't account for the incoming cash from pending `sell` orders.
  2. **AI Strategy:** The AI's default strategy of diversification was not suitable for a micro-portfolio, leading to multiple sub-minimum trade suggestions.
- **Comprehensive Solution:**
  1. **Sequential Trade Execution:** Refactored `TradeExecutor.execute_trades` to process all `sell` orders first, then requery the balance to get the updated cash amount before executing `buy` orders. This ensures buys are only attempted with capital that is actually available.
  2. **Enhanced AI Prompting:** Added a `SINGLE-POSITION MANDATE` to `prompt_template.md`. For portfolios under $50, the AI is now explicitly instructed to consolidate its investment into a single, high-conviction trade to ensure it meets minimum order sizes.
- **Impact:** The bot can now intelligently rebalance its portfolio without running into "insufficient funds" errors, and its strategy for small portfolios is much more robust, preventing failed trades.
- **Status:** ✅ PRODUCTION READY - The bot's trading and rebalancing logic is now significantly more reliable, especially for small portfolios.

---

### 🧹 Dust Position Handling (August 2025) - IMPLEMENTED ✅
- **Problem Solved:** The AI was generating `sell` orders with `0.0%` allocation for tiny "dust" positions (e.g., $0.001 worth of an asset), creating noisy and unnecessary warnings in the logs.
- **Root Cause:** Tiny residual balances from previous trades were being included in the AI's portfolio context.
- **Two-Layered Solution:**
  1. **Source Filtering:** Modified `KrakenAPI.get_comprehensive_portfolio_context` to filter out any crypto holding worth less than **$0.01** and making up less than **0.05%** of the portfolio. This prevents the AI from ever seeing dust.
  2. **Validation Safety Net:** Enhanced `TraderAgent._validate_trade_format` to gracefully skip any trade with a `0.0%` allocation that might still get through, logging it as an `INFO`-level "no-op" instead of a `WARNING`.
- **Files Modified:**
  - `bot/kraken_api.py`
  - `agents/trader_agent.py`
- **Impact:** The trading logs are now cleaner and more focused on meaningful actions. The system is more robust, as the bot will no longer attempt to trade insignificant dust balances.
- **Status:** ✅ PRODUCTION READY - The bot now gracefully ignores dust positions.

---

### 🌐 Connection Resilience with Retries (August 2025) - IMPLEMENTED ✅
- **Problem Solved:** Temporary network issues or Kraken API glitches could cause the entire trading cycle to fail.
- **Solution:** Implemented a robust retry mechanism in `KrakenAPI._query_api` with exponential backoff.
- **Features:**
  - Automatically retries failed requests up to 3 times.
  - Waits longer between each retry (1s, 2s, 4s) to handle temporary API load.
  - Intelligently distinguishes between temporary network/API errors (which should be retried) and critical application-level errors like "insufficient funds" (which should fail immediately).
- **Impact:** The bot is now much more resilient to transient network problems, increasing its overall reliability and uptime.
- **Status:** ✅ PRODUCTION READY - The bot can now gracefully handle temporary connection issues.

---

## 🏦 Enhanced Portfolio Awareness (August 2025)

**Objective:** Ensure the trading bot is always aware of current holdings using live Kraken API data, never making assumptions about portfolio state.

**Key Enhancements:**

### 📊 Comprehensive Portfolio Context (`bot/kraken_api.py`)
- **New Method:** `get_comprehensive_portfolio_context()` provides detailed portfolio analysis
- **Features:**
  - Live USD values for all holdings with real-time prices
  - Asset allocation percentages calculated automatically  
  - Distinction between cash, crypto, and forex assets
  - Tradeable assets identification for AI strategy decisions
  - Total equity calculation with proper asset categorization

### 🎯 Decision Engine Portfolio Integration (`bot/decision_engine.py`)
- **Enhanced Context Building:** Uses comprehensive portfolio data instead of basic balance lookup
- **Live Data Priority:** Always queries Kraken API, never assumes or uses cached data
- **Rich Context:** AI receives detailed allocation percentages, USD values, and tradeable asset lists

### 🤖 Strategic Agent Portfolio Integration (`agents/strategist_agent.py`)
- **Updated Method:** `get_portfolio_context()` now uses comprehensive portfolio data
- **Advanced Analytics:** Provides allocation percentages, USD values, and portfolio metrics
- **Enhanced Logging:** Detailed portfolio state logging for transparency

### ⚡ Trade Executor Portfolio Validation (`bot/trade_executor.py`)
- **Pre-Trade Validation:** `_validate_trade_against_holdings()` checks sufficient balance for sell orders
- **Portfolio Impact Logging:** Shows expected allocation changes before execution
- **Real-Time Equity:** Uses live portfolio value for percentage-based allocations
- **Smart Validation:** Prevents trades that would exceed available balances

### 🔄 7AM Review Integration
**Daily Startup Process:**
1. **Portfolio Discovery:** Live Kraken API query reveals exact current holdings
2. **Context Building:** Comprehensive portfolio data fed to AI for strategy decisions
3. **Trade Validation:** All proposed trades validated against actual balances
4. **Impact Analysis:** Portfolio allocation changes logged and analyzed

**Benefits:**
- ✅ **No Assumptions:** Bot always knows exact current state via Kraken API
- ✅ **Sell Order Safety:** Validates sufficient balance before attempting sales  
- ✅ **Allocation Awareness:** AI sees percentage breakdowns for smarter rebalancing
- ✅ **USD Value Clarity:** All holdings valued in USD for consistent decision-making
- ✅ **Trading Pair Recognition:** Automatic identification of assets that can be traded to USD

**Technical Implementation:**
- **Real-Time Pricing:** Live Kraken ticker data for accurate USD valuations
- **Asset Classification:** Separates cash (USD/USDC/USDT), crypto, and forex automatically
- **Comprehensive Logging:** Detailed portfolio state and trade impact visibility
- **Error Handling:** Graceful fallbacks if portfolio data unavailable

---

## 🤖 AI Portfolio Understanding Enhancement (August 2025)

**Critical Issue Resolved:** AI was receiving portfolio context but not generating trades due to misunderstanding of rebalancing capabilities.

**Problem Identified:**
- AI received portfolio data (e.g., "Current holdings: ADA $9.86, Cash $0.47") 
- AI understood it held assets but thought it couldn't trade due to "insufficient cash"
- AI didn't realize it could **SELL existing positions** to rebalance portfolio
- Generated empty trade lists with "DEFENSIVE_HOLDING" strategy instead of active rebalancing

**Comprehensive Solution:**

### 📝 Enhanced Prompt Template (`bot/prompt_template.md`)
- **Added PORTFOLIO REBALANCING section:** Explicitly explains AI can sell existing positions
- **Added SELL EXISTING HOLDINGS directive:** Clear instruction to generate sell orders for rebalancing
- **Added concrete example:** Shows exact JSON format for selling ADA and buying ETH/BTC
- **Clarified constraints:** Removed ambiguity about cash limitations vs rebalancing capabilities

### 🎯 Enhanced Portfolio Context (`agents/strategist_agent.py`)
- **Expanded portfolio description:** Now includes total portfolio value and allocation percentages
- **Added TRADING OPPORTUNITIES section:** Explicitly lists rebalancing capabilities
- **Cash constraint clarity:** Explains that limited cash doesn't prevent selling existing positions
- **Position-level details:** Shows allocation percentages for each holding

### 🔧 Fixed Trading Rules Formatting (`agents/strategist_agent.py`)
- **Corrected field references:** Fixed 'base_asset' → 'base' field mapping error
- **Added rebalancing guidance:** Clear rules about selling any currently held asset
- **Removed cash constraints:** Explicitly states "NO CASH CONSTRAINTS" for rebalancing
- **Strategic direction:** Added selling strategy explanation for portfolio transitions

### 🎯 AI Training Improvements
**Before:** 
```
AI sees: "ADA: $9.86, Cash: $0.47"
AI thinks: "Not enough cash to buy anything, must hold"
AI output: {"trades": [], "strategy": "DEFENSIVE_HOLDING"}
```

**After:**
```
AI sees: "ADA: $9.86 (95.4%), Cash: $0.47 (4.6%) - You can SELL any holdings to rebalance"
AI thinks: "I can sell ADA to buy ETH/BTC based on market analysis"
AI output: {"trades": [{"pair": "ADAUSD", "action": "sell", "allocation_percentage": 0.95}, {"pair": "ETHUSD", "action": "buy", "allocation_percentage": 0.60}]}
```

**Result:** AI now understands it can actively rebalance portfolios by selling existing positions to fund new investment strategies based on market analysis.

---

## Maintenance: Clean Slate Runbook (August 2025)

A new utility `cleanup_logs.py` provides a safe, Windows-friendly way to reset all bot-generated logs and caches before a fresh run.

- Location: project root (`cleanup_logs.py`)
- Default behavior: DRY-RUN (no deletion). Use `--execute` to actually delete.

Supported targets (selective or all):
- Directories: `logs/agent_transcripts/`, `logs/prompts/`
- Files: `logs/equity.csv`, `logs/rejected_trades.csv`, `logs/research_cache.json`, `logs/scheduler_multiagent.log`, `logs/scheduler.log`, `logs/thesis_log.md`, `logs/trades.csv`, `logs/coingecko_cache.json`, `logs/daily_research_report.md`

CLI

- Preview (dry-run default):
  - `python cleanup_logs.py`  (shows what would be deleted)
  - `python cleanup_logs.py --targets transcripts,trades`  (scope selection)
- Execute (with confirmation):
  - `python cleanup_logs.py --all --execute`
  - Add `--force` to skip interactive confirmation (CI): `python cleanup_logs.py --all --execute --force`
- Retention by age:
  - `python cleanup_logs.py --all --older-than 7`  (deletes only items older than 7 days; directories are pruned, not removed)
- Backup before deletion:
  - `python cleanup_logs.py --all --backup backups/logs_backup.zip --execute`
- Lock detection (Windows best-effort):
  - `python cleanup_logs.py --check-locks`
- Verbose per-path output:
  - `python cleanup_logs.py --verbose`

Safety & Notes
- Stop the bot (`scheduler_multiagent.py`) before executing; Windows may lock log files.
- The script prints a summary: Deleted, Skipped (missing/too-new), Locked (skipped), Failed.
- Exit codes: 0 success, 1 aborted, 2 failures.
- After cleanup, the script recreates `logs/agent_transcripts/` and `logs/prompts/` to avoid first-run issues.

Rationale
- Avoids accidental data loss with dry-run and explicit confirmation.
- Handles Windows file locks gracefully (skips locked, reports separately).
- Centralizes targets to keep maintenance DRY and auditable.

---

### Scheduler Robustness (August 2025) - IMPLEMENTED ✅
- Added immediate shutdown on `Ctrl+C` and concurrent-run guard to `scheduler_multiagent.py`.
- Features:
  - `Ctrl+C` terminates the scheduler immediately.
  - Manual, scheduled, and anomaly triggers respect a `pipeline_running` guard; concurrent runs are skipped with a warning.
  - Status panel (`[S]`) shows whether a pipeline is currently running.
- Impact: Prevents duplicate concurrent runs when monitoring continuously and honors instant shutdown when requested.

---

### Logging & Emoji Toggle (August 2025) - IMPLEMENTED ✅
- Added `LOG_EMOJI` env toggle with auto-detect of console encoding.
- On non-UTF consoles (common on Windows), emojis are disabled and ASCII fallbacks are used to prevent mojibake.

### Timestamp & Performance Context Hardening (August 2025) - IMPLEMENTED ✅
- Reflection & Strategist now parse timestamps as UTC and coerce equity to numeric:
  - Removed pandas inference warnings, ensured robust date math.
  - Prevented string subtraction errors in performance calculations.
- Strategist performance context now guards for insufficient/bad rows.

### Supervisor Summary Accuracy (August 2025) - IMPLEMENTED ✅
- `trades_approved` now reports TRUE only when at least one trade was executed successfully; defensive-hold shows FALSE.

---

### 🔍 CoinGecko Percent Change Validation & Fallbacks (August 2025) - IMPLEMENTED ✅
- Problem: 1h/24h/7d/30d percent changes sometimes appeared wrong or fabricated when CoinGecko omitted fields; UI defaulted missing values to 0.
- Solution:
  - Validation mode with env toggles; compare `/coins/markets` vs `/coins/{id}` (market_data) vs recomputed from `/coins/{id}/market_chart`.
  - If markets field missing or deviates beyond tolerance, fallback to coin overview; if still missing, fallback to recomputed time-series.
  - Never coerce missing fields to zero; downstream renders N/A. 30d is displayed consistently.
- Files Modified:
  - `agents/coingecko_agent.py`: Added `_fetch_coin_overview`, `_fetch_market_chart`, `_recompute_changes_from_chart`, `_log_validation`; integrated per-field provenance and fallbacks.
  - `agents/strategist_agent.py`: Render N/A instead of 0, include 30d, optional provenance note when validation enabled.
  - `agents/analyst_agent.py`: Consume structured numeric fields directly; removed brittle text parsing; skip tokens with missing values.
  - `bot/research_agent.py`: Display 1h/24h/7d/30d with N/A as needed; removed direction emojis tied to missing data.
- Env Config:
  - `COINGECKO_VALIDATE` = `1|true|yes` to enable validation & discrepancy logging (default off).
  - `COINGECKO_TOLERANCE_PCTPOINTS` = decimal tolerance in percentage points (default `0.2`).
- Logs & Provenance:
  - Validation records appended to `logs/coingecko_validation.jsonl` with markets/overview/recomputed side-by-side and per-field sources.
  - Strategist optionally shows a short "Data sources: markets/coin_overview/recomputed" hint per asset when validation is enabled.
- Impact: Eliminates fabricated-looking values, ensures percent changes are real-time and consistent with CoinGecko, improves model input fidelity.

---
