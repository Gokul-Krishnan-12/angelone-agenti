# AGENTS.md — Master Technical Guide & Knowledge Base

> **Single Source of Truth for AI Coding Agents** (Claude Code, Gemini CLI, Cursor, Antigravity, Codex) working on the Angel One SmartAPI Algorithmic Trading Application.  
> Whenever new features, strategies, risk rules, or API endpoints are added or modified in this repository, **you MUST update the relevant sections of this document** according to the [Agent Maintenance Protocol](#13-agent-maintenance-protocol-mandatory-on-new-changes).

---

## Table of Contents
1. [Executive Architecture Overview](#1-executive-architecture-overview)
2. [Repository Directory & Component Map](#2-repository-directory--component-map)
3. [Environment & Build Tooling](#3-environment--build-tooling)
4. [Trading Engine Lifecycle & Execution Architecture](#4-trading-engine-lifecycle--execution-architecture)
5. [Market Regime Classification & Kaufman Efficiency Ratio (KER)](#5-market-regime-classification--kaufman-efficiency-ratio-ker)
6. [Strategy Suite & Confluence Scoring System](#6-strategy-suite--confluence-scoring-system)
7. [Risk Management & Indian Statutory Friction Guard](#7-risk-management--indian-statutory-friction-guard)
8. [JSON-RPC 2.0 Bridge & IPC Communication](#8-json-rpc-20-bridge--ipc-communication)
9. [2-Way Telegram Bot Controller & Notifier](#9-2-way-telegram-bot-controller--notifier)
10. [Frontend UI & State Architecture](#10-frontend-ui--state-architecture)
11. [Walk-Forward Backtesting Engine](#11-walk-forward-backtesting-engine)
12. [Required Checks & Development Guidelines](#12-required-checks--development-guidelines)
13. [Agent Maintenance Protocol (Mandatory on New Changes)](#13-agent-maintenance-protocol-mandatory-on-new-changes)
14. [Safety & Security Rules (Non-Negotiable)](#14-safety--security-rules-non-negotiable)

---

## 1. Executive Architecture Overview

This repository is an **agentic intraday algorithmic trading desktop application** designed for Indian equities on the **National Stock Exchange (NSE)** via **Angel One SmartAPI** (`smartapi-python`).

```
┌────────────────────────────────────────────────────────┐
│                   React 18 Desktop UI                  │
│       (TypeScript, Tailwind CSS, Lucide, Zustand)      │
└───────────────────────────▲────────────────────────────┘
                            │ Electron IPC
┌───────────────────────────▼────────────────────────────┐
│                  Electron Main Process                 │
│              (src/main/python-bridge.ts)               │
└───────────────────────────▲────────────────────────────┘
                            │ JSON-RPC 2.0 (stdin / stdout)
┌───────────────────────────▼────────────────────────────┐
│                   Python Backend Core                  │
│              (uv-managed Python 3.9 - 3.12)            │
│  ┌──────────────────┐ ┌─────────────────┐ ┌─────────┐  │
│  │  Trading Engine  │ │ Confluence Gate │ │ Screener│  │
│  │ (Fast/Slow Loop) │ │  (25 Strategies)│ │  (KER)  │  │
│  └────────┬─────────┘ └────────┬────────┘ └────┬────┘  │
│           │                    │               │       │
│  ┌────────▼────────────────────▼───────────────▼─────┐  │
│  │   Risk Manager & Indian Statutory Friction Guard   │  │
│  └────────────────────────┬──────────────────────────┘  │
│                           │ REST & WebSocket            │
│  ┌────────────────────────▼──────────────────────────┐  │
│  │       SmartAPI Client (pyotp Headless 2FA)        │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Core Characteristics:
- **Headless 2FA Session Creation**: Automatically generates time-based TOTP passwords using `pyotp` from user-configured secrets, eliminating browser redirect requirements.
- **Local Persistence & Encryption**: User credentials, active positions, and custom configurations are encrypted using `cryptography.fernet` (AES-128-CBC with HMAC-SHA256) and saved in `~/.smartapi-agentic-trading/config.json`.
- **Pre-Trade Mathematical Edge**: Every signal must clear a **3-Family Confluence Gate**, a **50-EMA Trend Alignment Gate**, a **Market Regime Filter**, and a **1:2 Risk-Reward Target Geometry**.
- **Pre-Trade Friction Defense**: Models complete Indian statutory exchange charges (Brokerage, STT, Exchange Turnover, Stamp Duty, SEBI, GST). Automatically blocks trades where expected payoff $< 3.5\times$ regulatory friction.
- **Fail-Safe Trade Execution**: Live entries use `LIMIT` orders; positions are immediately protected with native exchange `STOPLOSS_LIMIT` orders on Angel One servers to prevent catastrophic slippage if the desktop app disconnects.

---

## 2. Repository Directory & Component Map

| Path | Purpose & Key Modules |
| :--- | :--- |
| [run_backend.py](file:///home/gokul/Desktop/angelone-agenti/run_backend.py) | Top-level entry point that invokes [backend/main.py](file:///home/gokul/Desktop/angelone-agenti/backend/main.py) for the JSON-RPC event loop. |
| [backend/main.py](file:///home/gokul/Desktop/angelone-agenti/backend/main.py) | JSON-RPC 2.0 request router over `sys.stdin` and `sys.stdout`. Dispatches calls to auth, engine, scanner, and config. |
| [backend/smartapi_client.py](file:///home/gokul/Desktop/angelone-agenti/backend/smartapi_client.py) | Singleton `SmartApiClient` wrapping `smartapi-python`. Handles headless TOTP login, session renewal, order placement/modification/cancellation, rate limiting, and historical data fetching. |
| [backend/trading_engine.py](file:///home/gokul/Desktop/angelone-agenti/backend/trading_engine.py) | Master trading engine orchestrator. Manages the dual-loop execution, order timeouts, native exchange SLs, partial profit booking, ATR trailing SLs, thesis invalidation, and EOD square-off. |
| [backend/risk_manager.py](file:///home/gokul/Desktop/angelone-agenti/backend/risk_manager.py) | Singleton `RiskManager`. Enforces 1R position sizing, daily loss caps (₹800), daily trade count caps (8 trades/day), market hours gating, and ATR trailing SL logic. |
| [backend/scanner.py](file:///home/gokul/Desktop/angelone-agenti/backend/scanner.py) | Multi-strategy scanner. Coordinates all 25 strategies, groups votes by signal family, applies confluence, trend alignment (50 EMA), regime, and 1:2 R:R geometry gates. |
| [backend/screener.py](file:///home/gokul/Desktop/angelone-agenti/backend/screener.py) | Dynamic macro universe screener. Evaluates Kaufman Efficiency Ratio (KER $\ge 0.28$), 20-day turnover ($\ge ₹40\text{ Cr}$), ATR% ($\ge 1.5\%$), and morning RVOL ($\ge 1.8$). |
| [backend/market_regime.py](file:///home/gokul/Desktop/angelone-agenti/backend/market_regime.py) | Quantitative market regime classifier (`TRENDING_BULL`, `TRENDING_BEAR`, `CHOPPY_RANGE`, `VOLATILE_EXPANSION`) using ADX, KER, 50 EMA, and Bollinger Band squeeze width. |
| [backend/market_hours.py](file:///home/gokul/Desktop/angelone-agenti/backend/market_hours.py) | Indian exchange market hours validator (09:15–15:30 IST), intraday cutoff detector (15:00/15:15 IST), and dynamic exchange trading holiday fetcher with disk cache. |
| [backend/notifier.py](file:///home/gokul/Desktop/angelone-agenti/backend/notifier.py) | Asynchronous Telegram alert dispatcher using thread pool executors for trade exits, partial bookings, and EOD summaries. |
| [backend/telegram_bot.py](file:///home/gokul/Desktop/angelone-agenti/backend/telegram_bot.py) | Inbound 2-way Telegram bot listener (`/status`, `/start`, `/stop`, `/squareoff`, `/positions`, `/help`). |
| [backend/ticker.py](file:///home/gokul/Desktop/angelone-agenti/backend/ticker.py) | WebSocket ticker manager wrapping SmartAPI SmartWebSocket for real-time tick streaming. |
| [backend/config.py](file:///home/gokul/Desktop/angelone-agenti/backend/config.py) | Configuration manager. Handles Fernet encryption of credentials, risk settings defaults, active trade persistence, and watchlist state. |
| [backend/fno_universe.py](file:///home/gokul/Desktop/angelone-agenti/backend/fno_universe.py) | List of 180+ liquid NSE F&O equities with SmartAPI token mappings. |
| [backend/nifty_universe.py](file:///home/gokul/Desktop/angelone-agenti/backend/nifty_universe.py) | Standard NIFTY 50 universe definition. |
| [backend/swing_screener.py](file:///home/gokul/Desktop/angelone-agenti/backend/swing_screener.py) | Daily multi-timeframe swing trading screener. |
| [backend/strategies/](file:///home/gokul/Desktop/angelone-agenti/backend/strategies/) | All 25 individual technical strategy classes implementing [BaseStrategy](file:///home/gokul/Desktop/angelone-agenti/backend/strategies/base.py). |
| [backend/backtest/](file:///home/gokul/Desktop/angelone-agenti/backend/backtest/) | Walk-forward backtesting suite with statutory Indian friction modeling, Yahoo Finance data caching, and Markdown reporting. |
| [backend/tests/](file:///home/gokul/Desktop/angelone-agenti/backend/tests/) | Pure offline pytest suite (330+ unit tests) using synthetic candle fixtures. |
| [src/main/](file:///home/gokul/Desktop/angelone-agenti/src/main/) | Electron main process: [python-bridge.ts](file:///home/gokul/Desktop/angelone-agenti/src/main/python-bridge.ts), [ipc-handlers.ts](file:///home/gokul/Desktop/angelone-agenti/src/main/ipc-handlers.ts), [preload.ts](file:///home/gokul/Desktop/angelone-agenti/src/main/preload.ts). |
| [src/renderer/](file:///home/gokul/Desktop/angelone-agenti/src/renderer/) | React 18 frontend: pages ([Dashboard](file:///home/gokul/Desktop/angelone-agenti/src/renderer/pages/Dashboard.tsx), [AgentControl](file:///home/gokul/Desktop/angelone-agenti/src/renderer/pages/AgentControl.tsx), [Orders](file:///home/gokul/Desktop/angelone-agenti/src/renderer/pages/Orders.tsx), [PaperTrade](file:///home/gokul/Desktop/angelone-agenti/src/renderer/pages/PaperTrade.tsx), [Settings](file:///home/gokul/Desktop/angelone-agenti/src/renderer/pages/Settings.tsx), [SystemGuide](file:///home/gokul/Desktop/angelone-agenti/src/renderer/pages/SystemGuide.tsx)), stores ([trading-store.ts](file:///home/gokul/Desktop/angelone-agenti/src/renderer/stores/trading-store.ts), [paper-trading-store.ts](file:///home/gokul/Desktop/angelone-agenti/src/renderer/stores/paper-trading-store.ts)). |
| [trading_system/](file:///home/gokul/Desktop/angelone-agenti/trading_system/) | High-frequency, event-driven async prototype for sub-second WebSocket bar aggregation and native two-legged order routing. |

---

## 3. Environment & Build Tooling

- **Python Runtime & Package Manager**: Python $\ge 3.9$ managed strictly via **uv**.
  - Provision virtual environment: `uv sync`
  - Run Python commands: `uv run python ...`
  - Add dependency: `uv add <package>`
- **Node.js Runtime & Frontend Tooling**: Node $\ge 18$, `npm`.
  - Install dependencies: `npm install`
  - Launch Electron dev app: `npm run dev`
  - Production build: `npm run build && npm run dist`

---

## 4. Trading Engine Lifecycle & Execution Architecture

The core engine is encapsulated in [backend/trading_engine.py](file:///home/gokul/Desktop/angelone-agenti/backend/trading_engine.py) (`TradingEngine`). It runs a continuous background thread (`_run_loop`) featuring decoupled fast and slow polling intervals.

### 4.1 Dual-Loop Execution Rhythm
1. **Fast Loop (Every 5 seconds)**:
   - Reconciles pending entry orders (`monitor_pending_orders`).
   - Evaluates active positions against live LTP (`monitor_positions`).
   - Checks native exchange stop-loss trigger levels.
   - Evaluates partial profit booking targets (Target 1).
   - Ratchets ATR trailing stop-loss orders on the exchange.
   - Cleans up positions manually closed on the Angel One mobile app.
2. **Slow Loop (Every 60 seconds)**:
   - Scans the market for new entry setups (`scan_and_trade`).
   - Clock-aligned dynamic re-screening across the F&O universe (`screener_engine.generate_daily_watchlist`): runs on initial engine startup and at scheduled market intervals (**09:30, 10:30, 11:30, 12:30, 13:30, 14:30 IST**). If a scheduled re-screen encounters transient network/quote timeouts, the engine automatically reschedules a 5-minute retry backoff (`_screener_retry_due_at = now_ts + 300`) while strictly preserving all active open trades in the dynamic watchlist.
   - Re-evaluates open positions for **Thesis Invalidation**.

### 4.2 Execution Modes
- **`confirm` Mode (Default & Recommended)**: Generates high-confluence trade setups, calculates 1R sizing, stop-loss, and target geometry, and streams them to the React UI for 1-click manual authorization.
- **`auto` Mode**: Autonomously executes trades when:
  1. Market hours check passes (`risk_manager.can_trade() == True`).
  2. Signal confidence $\ge 85\%$.
  3. Confluence score $\ge 3$ (minimum 3 independent families voting).
  4. Symbol is not already an open active trade.

### 4.3 Two-Legged Order Routing & Pending Timeout
```
Signal Triggered
       │
       ▼
1R Position Sizer (max ₹4,000 margin, 5x MIS)
       │
       ▼
LIMIT Entry Order placed at entryPrice
       │
       ├─► Sits in pending_orders (max 60 seconds)
       │         │
       │         ├─► If unfilled after 60s ──► smart_api_client.cancel_order()
       │         │
       │         └─► On COMPLETE fill:
       │                   │
       │                   ▼
       │             Place Native Exchange STOPLOSS_LIMIT Order on Angel One
       │             (trigger = stop_loss, limit = stop_loss * 0.99 / 1.01)
       ▼
Add to active_trades & persist to disk
```

### 4.4 Partial Profit Booking & Breakeven SL
When a trade reaches an asymmetric setup ($R:R > 2.2$):
- **Target 1**: Placed at $+2.0R$.
- **Target 2**: Full runner target.
- **Trigger Condition**: When LTP reaches Target 1 and expected profit $\ge ₹250$ (safeguard against ₹20 broker fee drag):
  1. Closes $50\%$ of the quantity with an immediate exit `LIMIT` order.
  2. Cancels the original full-quantity exchange stop-loss order.
  3. Ratchets the remaining $50\%$ position's stop-loss to **Breakeven (entry price)**.
  4. Places a new exchange `STOPLOSS_LIMIT` order at breakeven for the remaining runner shares.
  5. Dispatches a Telegram `PARTIAL_TARGET` alert.

### 4.5 ATR Trailing Stop-Loss Ratchet
- Controlled by `trailingSlEnabled`, `trailingSlAtrMultiplier` ($2.0\times$ default), and `trailingSlProfitCushionR` ($+1.0R$ default).
- Trailing **does not engage immediately**; price must advance at least $+1.0R$ in profit.
- Once activated, SL ratchets to at least breakeven, trailing $2.0 \times \text{ATR}$ behind the high/low water mark.
- When ratcheted, the engine executes `smart_api_client.modify_order` to update the exchange-side `STOPLOSS_LIMIT` order on Angel One's servers.

### 4.6 Graduated Thesis Invalidation (Position Re-Evaluation)
Open positions are checked every 60 seconds against current market signals:
1. **Rule 1 (Strong Opposing Signal)**: If $\ge 2$ opposing signals fire with $0$ supporting signals $\rightarrow$ Immediate thesis exit.
2. **Rule 2 (Weak Conviction)**: If $0$ supporting signals, position is in loss, and held for $\ge 15$ minutes $\rightarrow$ Immediate exit.
3. **Rule 3 (Time Decay)**: If held for $\ge 45$ minutes without hitting target $\rightarrow$ Stop-loss is tightened to Breakeven.
4. **Rule 4 (Thesis Valid)**: If supporting signals $> 0 \rightarrow$ Position held.

### 4.7 End of Day Square-Off & Daily Summary
- At **15:15 IST** (or when daily loss limit is hit), the engine calls `square_off_all()`.
- Cancels all resting exchange stop-loss orders and exits all open positions.
- Fetches completed orders from Angel One and calls the live `estimateCharges` SmartAPI endpoint.
- Computes exact Brokerage, STT, turnover charges, GST, Gross P&L, and Net P&L.
- Dispatches an EOD summary alert via Telegram and stops the engine.

---

## 5. Market Regime Classification & Kaufman Efficiency Ratio (KER)

Located in [backend/market_regime.py](file:///home/gokul/Desktop/angelone-agenti/backend/market_regime.py) and [backend/screener.py](file:///home/gokul/Desktop/angelone-agenti/backend/screener.py).

### 5.1 Kaufman Efficiency Ratio (KER) Formulation
Quantifies the ratio of directional price travel to total noise/volatility over a 20-period lookback window:

$$\text{Direction} = | \text{Close}_t - \text{Close}_{t-N} |$$

$$\text{Volatility} = \sum_{i=0}^{N-1} | \text{Close}_{t-i} - \text{Close}_{t-i-1} |$$

$$\text{KER} = \frac{\text{Direction}}{\text{Volatility}} \in [0.0, 1.0]$$

- $\text{KER} \ge 0.28$: Clean, directional momentum trend.
- $\text{KER} < 0.25$: Choppy, noisy, mean-reverting regime.

### 5.2 Market Regime States & Trade Gating
Evaluated using ADX(14), +DI/-DI, KER(20), 50 EMA, and Bollinger Band Squeeze width ($< 1.8\%$ bandwidth):

| Market Regime | Technical Criteria | Permitted Trades | Blocked Trades |
| :--- | :--- | :--- | :--- |
| **`TRENDING_BULL`** | ADX $\ge 20$, Close $> 50$ EMA, +DI $>$-DI, KER $\ge 0.25$ | BUY Breakouts, BUY Trend Continuation | Counter-trend SELL shorts |
| **`TRENDING_BEAR`** | ADX $\ge 20$, Close $< 50$ EMA, -DI $> $+DI, KER $\ge 0.25$ | SELL Breakouts, SELL Trend Continuation | Counter-trend BUY longs |
| **`CHOPPY_RANGE`** | ADX $< 20$ OR KER $< 0.25$ OR Bollinger Squeeze $< 1.8\%$ | Mean Reversion, Range Oscillators | **ALL Breakout & Trend entries blocked** (prevents whipsaws) |
| **`VOLATILE_EXPANSION`** | Outsized candle expansion / transitional volatility | High-conviction structure/volume setups | Aggressive breakouts |

### 5.3 Macro Universe Screening Pipeline (Top 35 Stocks)
Candidates from the 180+ F&O universe must pass 5 quantitative gates to be included in the dynamic watchlist:
1. **Price Floor**: $\text{LTP} \ge ₹150$ (eliminates penny stocks with high bid-ask friction).
2. **20-Day Average Daily Turnover**: $\ge ₹40\text{ Crore}$ (guarantees institutional liquidity).
3. **Daily ATR%**: $\ge 1.5\%$ (ensures sufficient intraday expansion range).
4. **Kaufman Efficiency Ratio (20D)**: $\text{KER} \ge 0.28$ (screens out sideways consolidations).
5. **Morning RVOL (after 09:45 IST)**: $\ge 1.8\times$ average relative volume.

### 5.4 Resilient Data Fetching & Auto-Reauthentication
- **HTTP Keep-Alive Connection Pooling**: Configured a persistent `requests.Session` with `HTTPAdapter(pool_connections=25, pool_maxsize=50, max_retries=Retry(total=3, backoff_factor=0.3, status_forcelist=[429, 500, 502, 503, 504]))` and patched `SmartApi.smartConnect.requests.request = self.http_session.request`. This eliminates continuous TCP 3-way handshake and TLS renegotiation churn that previously triggered Angel One WAF socket drops (`RemoteDisconnected`, `Connection aborted`).
- **SmartAPI Timeout Calibration**: Hardcoded library default of 7 seconds was overridden with a 20-second connection & read timeout (`SmartConnect(timeout=20)` and `self.smart_api.timeout = 20`) to eliminate `requests.exceptions.ReadTimeout` errors during peak-hour batch candle and quote requests.
- **Exhaustive Headless Session Renewal & Network Retry**: All data endpoints (`getCandleData`, `getMarketData`, `rmsLimit`, `holding`, `tradeBook`, `position`, `orderBook`, `placeOrder`, `cancelOrder`, `modifyOrder`, `estimateCharges`) are wrapped by `_execute_with_auth_retry()`. Intercepts HTTP errors and response bodies containing `AG8001`, `AG8002`, `AG8003` ("Token missing"), `AB1004`, or expired session states, immediately executing a headless TOTP re-login via `pyotp` and retrying the failed call seamlessly. In addition, transient network glitches (`remotedisconnected`, `connection aborted`, `read timeout`) are caught with an exponential backoff retry loop (up to 3 attempts) before failing.
- **Chunked Quote Fetching with Pacing**: Batch quote fetches across the 180+ F&O universe are executed in chunks of 50 with a 0.5s inter-chunk pacing delay and up to 3 retry attempts per chunk (1.5s delay) to ensure temporary exchange quote hiccups do not abort screening.
- **Clean Subprocess Logging**: Replaced raw `print()` statements in `backend/scanner.py` with `logger.warning()` to prevent unformatted non-JSON messages from corrupting the Electron JSON-RPC standard I/O pipe.

---

## 6. Strategy Suite & Confluence Scoring System

Located in [backend/scanner.py](file:///home/gokul/Desktop/angelone-agenti/backend/scanner.py) and [backend/strategies/](file:///home/gokul/Desktop/angelone-agenti/backend/strategies/).

### 6.1 Strategy Family Classification & Voting Rules
Each signal family counts as **exactly ONE vote** in the confluence score, regardless of how many individual strategies within that family fire simultaneously:

```
┌────────────────────────────────────────────────────────────────────────────┐
│                             8 SIGNAL FAMILIES                              │
├──────────────┬─────────────────────────────────────────────────────────────┤
│ 1. Breakout  │ donchian_breakout, keltner_breakout, bollinger_breakout     │
│ 2. Structure │ institutional_absorption, order_block_fvg,                  │
│              │ volume_delta_divergence, cpr_breakout_reversal             │
│ 3. Volume    │ cmf_accumulation                                            │
│ 4. Intraday  │ vwap_bounce, opening_range_breakout                         │
│ 5. Reversal  │ liquidity_grab_reversal, gap_fill                           │
│ 6. Trend     │ ema_crossover, supertrend, psar_trend, adx_momentum         │
│ 7. Momentum  │ macd_cross, rsi_reversal, tsi_cross                         │
│ 8. Oscillator│ stochastic_reversal, stoc_rsi, cci_reversal, williams_r,    │
│   (Max 1 Vote) awesome_oscillator, mfi_exhaustion                          │
└──────────────┴─────────────────────────────────────────────────────────────┘
```

### 6.2 Pre-Trade Gating Pipeline
Every candidate signal must clear the following sequentially:
1. **Market Hours Window**: No entries in opening chaos (09:15–09:30 IST); entries allowed 09:30–11:45 IST and 13:00–15:00 IST.
2. **Trend Alignment Gate**:
   - `BUY` signals require $\text{Close} \ge 50\text{ EMA}$.
   - `SELL` signals require $\text{Close} \le 50\text{ EMA}$.
3. **Confluence Gate**: $\text{Confluence Score} \ge 3$ independent signal families.
4. **Market Regime Gate**: `is_trade_allowed_by_regime()` verifies current symbol regime.
5. **Stop-Loss Minimum Floor**: Enforces a minimum $1.0\%$ stop-loss width to prevent noise stop-outs.
6. **1:2 R:R Geometry Target**: Targets are recalculated to guarantee at least $1:2$ Risk-to-Reward ratio against the widened SL buffer.

### 6.3 Active Alpha Strategies vs Pruned Strategies
Based on walk-forward backtest analysis under Indian statutory friction:
- **Enabled (Alpha Positive)**:
  - Breakouts: `donchian_breakout`, `keltner_breakout`, `bollinger_breakout`
  - Institutional: `institutional_absorption`, `order_block_fvg`, `volume_delta_divergence`
  - Intraday & Structural: `cpr_breakout_reversal`, `opening_range_breakout`, `liquidity_grab_reversal`, `gap_fill`, `cmf_accumulation`
- **Disabled by Default (Pruned due to Fee Drag / Negative Expectancy)**:
  - `psar_trend` (-₹8,575 backtest loss, lag whipsaw)
  - `ema_crossover` (-₹2,201 backtest loss)
  - `vwap_bounce` (88.9% stop-loss rate in rangebound markets)
  - `williams_r`, `cci_reversal`, `adx_momentum`, `rsi_reversal`, `stochastic_reversal`, `stoc_rsi`, `awesome_oscillator`, `mfi_exhaustion`, `supertrend`, `macd_cross`.

---

## 7. Risk Management & Indian Statutory Friction Guard

Located in [backend/risk_manager.py](file:///home/gokul/Desktop/angelone-agenti/backend/risk_manager.py) and [backend/backtest/engine.py](file:///home/gokul/Desktop/angelone-agenti/backend/backtest/engine.py).

### 7.1 Strict 1R Position Sizing
Positions are sized purely on risk budget in INR, constrained by maximum capital ceiling and 5x MIS leverage:

$$\text{Per-Share Risk} = | \text{Price} - \text{StopLoss} |$$

$$\text{Raw Quantity} = \left\lfloor \frac{\text{Risk Budget (default ₹500)}}{\text{Per-Share Risk}} \right\rfloor$$

$$\text{Max Allowed Quantity} = \left\lfloor \frac{\text{Max Capital (default ₹4,000)} \times \text{Leverage (5.0)}}{\text{Price}} \right\rfloor$$

$$\text{Quantity} = \max(1, \min(\text{Raw Quantity}, \text{Max Allowed Quantity}))$$

### 7.2 Portfolio Circuit Breakers
- **Daily Trade Limit**: Maximum **8 trades per day** (prevents overtrading and fee churn).
- **Max Daily Loss**: **₹800** (triggers immediate square-off and halts new entries).
- **Max Simultaneous Positions**: **4 positions**.
- **No New Trades After**: **15:00 IST**.
- **Mandatory Square-Off**: **15:15 IST**.

### 7.3 Complete Indian Statutory Friction Model & Live EstimateCharges API
Calculated for both live estimates and backtesting:

| Component | NSE Cash Intraday MIS Rate |
| :--- | :--- |
| **Brokerage** | $\min(₹20, 0.1\% \times \text{Turnover})$ per leg (Angel One official tariff; flat ₹40 round-trip max) |
| **Securities Transaction Tax (STT)** | $0.025\%$ on the **Sell** side turnover |
| **Exchange Transaction Charges** | $0.00325\%$ of total round-trip turnover |
| **SEBI Turnover Charges** | $₹10 \text{ per Crore} = 0.0001\%$ of round-trip turnover |
| **Stamp Duty** | $0.003\%$ on the **Buy** side turnover |
| **Goods & Services Tax (GST)** | $18\%$ applied to $(\text{Brokerage} + \text{Exchange Charges} + \text{SEBI Charges})$ |

### 7.4 Angel One Live `estimateCharges` & Pre-Trade Friction Guard
1. **Live Angel One API Integration**:
   - Uses `POST /rest/secure/angelbroking/brokerage/v1/estimateCharges` via `smart_api_client.estimate_round_trip_charges(...)`.
   - Prepares and transmits a multi-leg batch (`orders: [entry_leg, exit_leg]`) in a single network round-trip, receiving exact exchange breakdown from Angel One's servers.
2. **High-Speed Caching (0.018 ms vs 100 ms)**:
   - Evaluated round-trip charges are cached for 5 minutes (`_charges_cache`) keyed by `(symbol, entry, target, qty, product, direction)`.
   - Repeated checks during active market evaluation complete in **sub-millisecond time** (0.018 ms), avoiding execution loop delays.
3. **Ultra-Fast Local Fallback (0.001 ms)**:
   - `SmartApiClient.calculate_statutory_charges_fast(...)` provides a zero-latency fallback matching Angel One's exact calculation structure when offline or if network hiccups occur.
4. **Pre-Trade Friction Threshold ($3.5\times$)**:
   - Before entering any trade, the engine verifies:

$$\text{Expected Net Gain} = (\text{Target} - \text{EntryPrice}) \times \text{Quantity}$$

$$\text{Trade Permitted IF: } \text{Expected Net Gain} \ge 3.5 \times \text{Estimated Round-Trip Friction}$$

   - If expected gain is less than $3.5\times$ round-trip friction, the setup is **strictly rejected** to prevent fee churn.
5. **Pre-Trade Friction Evaluation**:
   - Executes automatically under the hood within `TradingEngine.execute_signal(...)` without cluttering the main dashboard UI.

---

## 8. JSON-RPC 2.0 Bridge & IPC Communication

Located in [src/main/python-bridge.ts](file:///home/gokul/Desktop/angelone-agenti/src/main/python-bridge.ts) and [backend/main.py](file:///home/gokul/Desktop/angelone-agenti/backend/main.py).

### 8.1 Wire Protocol
The Electron main process communicates with the Python backend over standard `stdin` and `stdout` using newline-delimited JSON-RPC 2.0 messages:

**Request Format**:
```json
{"jsonrpc": "2.0", "id": 1, "method": "execute_signal", "params": {"signal": {...}}}
```

**Response Format**:
```json
{"jsonrpc": "2.0", "id": 1, "result": {"executed": true}}
```

**Push Event Format (Python $\rightarrow$ Electron $\rightarrow$ Renderer)**:
```json
{"event": "agent:signal", "data": {"tradingsymbol": "RELIANCE", "confluenceScore": 3, ...}}
```

### 8.2 Inventory of JSON-RPC Methods

| Method | Parameters | Description |
| :--- | :--- | :--- |
| `login` | `apiKey`, `clientCode`, `pin`, `totpSecret` | Authenticates headlessly with SmartAPI, launches WebSocket ticker. |
| `check_session` | None | Checks cached token validity; auto-renews with TOTP secret if expired. |
| `logout` | None | Terminates session and stops WebSocket ticker. |
| `start_agent` | `{"mode": "auto" \| "confirm"}` | Launches the trading engine loop in specified mode. |
| `stop_agent` | None | Stops the trading engine background loop. |
| `agent_status` | None | Returns engine state (`{"running": bool, "mode": str}`). |
| `execute_signal` | `{"signal": {...}}` | Submits a 1-click execution request from the UI. |
| `scan_now` / `agent_scan_now` | None | Triggers immediate on-demand screening and scan across top stocks. |
| `get_positions` | `{"force": bool}` | Returns live net and day positions from Angel One. |
| `get_orders` | `{"force": bool}` | Returns full order book history. |
| `get_margins` | `{"force": bool}` | Returns available cash and equity margin details. |
| `estimate_charges` | `{"orders": [...]}` | Queries Angel One live API for exact fee/tax breakdown. |
| `place_order` | SmartAPI order params | Directly places an exchange order. |
| `cancel_order` | `variety`, `order_id` | Cancels an active or pending order. |
| `modify_order` | `order_id`, `price`, `trigger_price` | Modifies resting order parameters. |
| `get_historical` | `instrument_token`, `from_date`, `to_date`, `interval` | Returns OHLCV candle array. |
| `ticker_subscribe` | `{"tokens": [...]}` | Subscribes tokens to real-time WebSocket ticks. |
| `ticker_unsubscribe` | `{"tokens": [...]}` | Unsubscribes tokens from WebSocket ticks. |
| `get_settings` | None | Retrieves decrypted risk and strategy settings. |
| `save_settings` | `dict` | Persists updated settings and restarts Telegram bot if needed. |
| `settings_reset` | None | Restores default risk and strategy parameters. |
| `watchlist_get` | None | Retrieves user watchlist array. |
| `watchlist_add` | `{"symbol": str}` | Appends symbol to watchlist. |
| `watchlist_remove` | `{"symbol": str}` | Removes symbol from watchlist. |
| `swing_scan` | `{"limit": int}` | Executes multi-timeframe swing screener scan. |
| `market_status` | None | Returns current market status (open, closed, holiday info). |
| `telegram_test` | `{"botToken": str, "chatId": str}` | Dispatches a test connectivity message to Telegram. |

---

## 9. 2-Way Telegram Bot Controller & Notifier

Located in [backend/telegram_bot.py](file:///home/gokul/Desktop/angelone-agenti/backend/telegram_bot.py) and [backend/notifier.py](file:///home/gokul/Desktop/angelone-agenti/backend/notifier.py).

### 9.1 Inbound Remote Commands
The background long-polling daemon supports real-time smartphone control:
- `/status` — Returns engine state, open position count, daily P&L, available margin, and market status.
- `/start auto` or `/start confirm` — Starts engine in designated mode.
- `/stop` — Halts the trading engine loop.
- `/squareoff` — **Emergency Kill-Switch**: Immediately cancels all SLs, squares off all open positions, and stops the engine.
- `/positions` — Lists all open positions with live P&L and entry prices.
- `/help` — Displays command menu.

### 9.2 Outbound Event Notifications
Dispatches formatted HTML alerts asynchronously:
- **Trade Exit Alert**: Notifies on target hit, stop-loss hit, or thesis exit with ₹ P&L and percentage return.
- **Partial Profit Booking Alert**: Notifies on Target 1 fill and confirms stop-loss moved to breakeven.
- **EOD Session Summary**: Full daily P&L breakdown including executed order count, win rate, gross P&L, broker commission, and net P&L.

---

## 10. Frontend UI & State Architecture

Built with **React 18**, **TypeScript**, **Tailwind CSS**, and **Zustand**.

### 10.1 Key Pages ([src/renderer/pages/](file:///home/gokul/Desktop/angelone-agenti/src/renderer/pages/))
- [Dashboard.tsx](file:///home/gokul/Desktop/angelone-agenti/src/renderer/pages/Dashboard.tsx): Margin health, realized/unrealized P&L, daily win rate, quick action controls.
- [AgentControl.tsx](file:///home/gokul/Desktop/angelone-agenti/src/renderer/pages/AgentControl.tsx): Master agent cockpit, Mode toggle (Auto/Confirm), streaming Confluence Signal Cards with 1-click execution, live activity logs.
- [Orders.tsx](file:///home/gokul/Desktop/angelone-agenti/src/renderer/pages/Orders.tsx): Live order book, open positions, closed trade history.
- [PaperTrade.tsx](file:///home/gokul/Desktop/angelone-agenti/src/renderer/pages/PaperTrade.tsx): Real-time simulated paper trading engine with synthetic execution, SL/TP simulation, session statistics, sandbox activity logs, and a dedicated Rejected Setups tab with 1-click clearance.
- [Settings.tsx](file:///home/gokul/Desktop/angelone-agenti/src/renderer/pages/Settings.tsx): SmartAPI credentials modal, risk management sliders, strategy toggles, Telegram configuration, watchlist editor.
- [SystemGuide.tsx](file:///home/gokul/Desktop/angelone-agenti/src/renderer/pages/SystemGuide.tsx): Comprehensive interactive architectural guide explaining every strategy, confluence, KER screener, and friction guard.
- [SwingScreener.tsx](file:///home/gokul/Desktop/angelone-agenti/src/renderer/pages/SwingScreener.tsx): Multi-day swing trade candidate finder.
- [Watchlist.tsx](file:///home/gokul/Desktop/angelone-agenti/src/renderer/pages/Watchlist.tsx): Watchlist management with live LTP updates.

### 10.2 Zustand Stores
- [trading-store.ts](file:///home/gokul/Desktop/angelone-agenti/src/renderer/stores/trading-store.ts): Manages live trading state, pending confluence signals, open positions, settings, and agent status.
- [paper-trading-store.ts](file:///home/gokul/Desktop/angelone-agenti/src/renderer/stores/paper-trading-store.ts): Full in-memory paper trading simulation with local persistence (`localStorage`), simulated fills, and automated P&L tracking.

---

## 11. Walk-Forward Backtesting Engine

Located in [backend/backtest/](file:///home/gokul/Desktop/angelone-agenti/backend/backtest/).

### 11.1 Execution Command
```bash
uv run python -m backend.backtest.run_backtest \
    --period 60d \
    --interval 15m \
    --capital 40000 \
    --universe fno \
    --top-momentum 15 \
    --output backtest_report.md
```

### 11.2 Key CLI Parameters
- `--period`: Simulation window (`30d`, `60d`, `6mo`, `1y`).
- `--interval`: Bar size (`5m`, `15m`, `1h`, `1d`).
- `--capital`: Trade allocation in INR (default: `40000.0`).
- `--confluence`: Minimum strategy family agreement gate (default: `2`).
- `--min-rr`: Minimum target risk-reward ratio (default: `1.8`).
- `--trailing-atr`: ATR trailing stop-loss multiplier (default: `2.0` after `+1.0R` cushion).
- `--blacklist`: Space-delimited symbols to exclude.

---

## 12. Required Checks & Development Guidelines

### 12.1 Mandatory Quality Gates
Before committing or merging any code changes, **all of the following checks must pass**:

```bash
# Python Backend Verification
uv run ruff check backend/ run_backend.py     # PEP 8 Linting
uv run ruff format backend/ run_backend.py    # Formatting check
uv run pytest                                 # Run 330+ unit tests

# Frontend Verification
npm run lint                                  # ESLint checks
npm run typecheck                             # TypeScript compiler check
npm run build                                 # Production build bundle check
```

### 12.2 Unit Test Writing Rules
- All strategy signals must be **pure functions** (`DataFrame -> List[Dict]`).
- Do **NOT** make real HTTP requests or connect to Angel One SmartAPI in unit tests.
- Use the synthetic candle fixtures defined in [backend/tests/conftest.py](file:///home/gokul/Desktop/angelone-agenti/backend/tests/conftest.py).
- Any change to risk management, strategy calculations, screener logic, or JSON-RPC methods must include corresponding unit tests in [backend/tests/](file:///home/gokul/Desktop/angelone-agenti/backend/tests/).

---

## 13. Agent Maintenance Protocol (Mandatory on New Changes)

> **CRITICAL RULE FOR ALL AI CODING AGENTS**:  
> To keep the codebase synchronized and fast for subsequent prompts, **whenever you introduce changes to this repository, you MUST update this `AGENTS.md` file (and mirror `agent.md`)**.

Follow this checklist whenever modifying code:

| What Changed | Required Updates in `AGENTS.md` |
| :--- | :--- |
| **New Strategy Added** | 1. Add strategy to [Section 6.1 (Strategy Families)](#61-strategy-family-classification--voting-rules).<br>2. Add strategy to the active alpha list in Section 6.3.<br>3. Document default enabled status in [backend/config.py](file:///home/gokul/Desktop/angelone-agenti/backend/config.py). |
| **Risk / Sizing Parameters Modified** | 1. Update [Section 7 (Risk Management)](#7-risk-management--indian-statutory-friction-guard) with new formulas or thresholds.<br>2. Update default values in Section 4. |
| **New JSON-RPC Method Added** | 1. Document method name, parameters, and return value in [Section 8.2 (RPC Inventory)](#82-inventory-of-json-rpc-methods).<br>2. Update IPC bridge mapping in [src/shared/ipc-channels.ts](file:///home/gokul/Desktop/angelone-agenti/src/shared/ipc-channels.ts). |
| **Market Regime or Screener Changed** | 1. Update thresholds and rules in [Section 5 (Market Regime & KER)](#5-market-regime-classification--kaufman-efficiency-ratio-ker).<br>2. Update trade gating rules table. |
| **Trading Engine Lifecycle Modified** | 1. Update [Section 4 (Trading Engine Lifecycle)](#4-trading-engine-lifecycle--execution-architecture) diagrams and steps.<br>2. Call out any changes to order varieties, timeouts, or trailing logic. |
| **Telegram Bot Commands Added** | 1. Document new command in [Section 9 (Telegram Bot)](#9-2-way-telegram-bot-controller--notifier). |
| **Frontend Pages / Stores Modified** | 1. Update [Section 10 (Frontend UI & State)](#10-frontend-ui--state-architecture). |

---

## 14. Safety & Security Rules (Non-Negotiable)

1. **Zero Credential Exposure**:
   - **NEVER** request, print, hardcode, log, or commit SmartAPI credentials (API Key, Client Code, Password/MPIN, TOTP Secret, JWT Tokens).
   - Credentials are submitted only via the frontend Settings modal and stored encrypted using `Fernet` in `~/.smartapi-agentic-trading/config.json`.
2. **Real Capital Caution**:
   - This application places real exchange orders on the National Stock Exchange.
   - Any modification to order routing, position sizing, risk limits, or stop-loss handling must be treated as **high-risk**.
   - Always verify changes with unit tests and recommend paper trading before live execution.
