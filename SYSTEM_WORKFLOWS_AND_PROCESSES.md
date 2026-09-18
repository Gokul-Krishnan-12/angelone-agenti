# Angel One SmartAPI Algorithmic Trading Application
## Complete System Architecture & Operational Workflows Guide

This document provides an end-to-end technical and operational explanation of how the entire trading system operates—from the moment the application boots in the morning to the final end-of-day square-off and reconciliation.

---

## Table of Contents
1. [High-Level System Architecture](#1-high-level-system-architecture)
2. [Workflow 1: System Boot, Headless Authentication & Session Management](#2-workflow-1-system-boot-headless-authentication--session-management)
3. [Workflow 2: Macro Screening & Dynamic Watchlist Generation](#3-workflow-2-macro-screening--dynamic-watchlist-generation)
4. [Workflow 3: Market Regime Classification & Structural Gating](#4-workflow-3-market-regime-classification--structural-gating)
5. [Workflow 4: Real-Time Scanning & Strategy Confluence Gate](#5-workflow-4-real-time-scanning--strategy-confluence-gate)
6. [Workflow 5: Pre-Trade Statutory Friction Defense](#6-workflow-5-pre-trade-statutory-friction-defense)
7. [Workflow 6: 1R Position Sizing & Two-Legged Order Execution](#7-workflow-6-1r-position-sizing--two-legged-order-execution)
8. [Workflow 7: Active Trade Monitoring & Dynamic Exits](#8-workflow-7-active-trade-monitoring--dynamic-exits)
9. [Workflow 8: End-of-Day Square-Off & Post-Market Reconciliation](#9-workflow-8-end-of-day-square-off--post-market-reconciliation)
10. [Workflow 9: Remote Surveillance & Emergency Telegram Controls](#10-workflow-9-remote-surveillance--emergency-telegram-controls)

---

## 1. High-Level System Architecture

The project is structured into two decoupled processes communicating via asynchronous **JSON-RPC 2.0 over standard I/O (stdin/stdout)**:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        React 18 Desktop Client                         │
│       • Dashboard & Live Charts       • Confirm Mode Trade Card        │
│       • Risk & Strategy Toggles       • Zustand Local State Store      │
└───────────────────────────────────▲────────────────────────────────────┘
                                    │ Electron IPC
┌───────────────────────────────────▼────────────────────────────────────┐
│                        Electron Main Process                           │
│                      (src/main/python-bridge.ts)                       │
└───────────────────────────────────▲────────────────────────────────────┘
                                    │ JSON-RPC 2.0 (stdin / stdout)
┌───────────────────────────────────▼────────────────────────────────────┐
│                         Python Core Engine                             │
│  ┌────────────────────────┐  ┌──────────────────────────────────────┐  │
│  │ Dual-Loop Engine       │  │ Quantitative Gating                  │  │
│  │ • 5s Fast Watchdog     │  │ • Confluence Gate (8 Signal Families)│  │
│  │ • 60s Strategy Scanner │  │ • Market Regime Gate (ADX/KER)       │  │
│  │ • Native SL Ratchet    │  │ • Pre-Trade Friction Guard (3.5x)    │  │
│  └───────────┬────────────┘  └──────────────────┬───────────────────┘  │
│              └────────────────┬─────────────────┘                      │
│                               │ REST & WebSocket                       │
│  ┌────────────────────────────▼─────────────────────────────────────┐  │
│  │ SmartAPI Gateway                                                 │  │
│  │ • Headless pyotp 2FA Engine      • Live estimateCharges API      │  │
│  │ • Connection Pooling (25/50)     • SmartWebSocket Tick Feed      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Workflow 1: System Boot, Headless Authentication & Session Management

```
App Launch ──► Decrypt ~/.smartapi-agentic-trading/config.json (AES-128 Fernet)
                   │
                   ▼
             Generate TOTP Password via pyotp (Zero Browser Redirects)
                   │
                   ▼
             POST /rest/auth/partner/v1/generate-token
                   │
                   ▼
             Set Persistent Session with Connection Pooling (25/50 pool)
```

1. **Local Credential Decryption**:
   - The user's API Key, Client ID, Pin, and TOTP Secret are stored in `~/.smartapi-agentic-trading/config.json`.
   - All credentials are encrypted on disk using `cryptography.fernet` (AES-128-CBC with HMAC-SHA256 authenticated signatures).
2. **Headless 2FA Session Creation**:
   - Instead of redirecting to an external browser login, the backend uses `pyotp.TOTP(totp_secret).now()` to calculate the live time-based 6-digit one-time password.
   - It submits the credentials to Angel One's login endpoint to obtain the `jwtToken`, `refreshToken`, and `feedToken`.
3. **HTTP Keep-Alive Connection Pooling**:
   - Configures a persistent `requests.Session` with `HTTPAdapter(pool_connections=25, pool_maxsize=50, max_retries=Retry(total=3, backoff_factor=0.3))`.
   - Patches `SmartApi.smartConnect.requests.request` so that requests reuse existing open TCP sockets. This eliminates continuous TLS renegotiations and prevents Angel One's WAF from dropping sockets (`RemoteDisconnected`).
4. **Self-Healing Session Renewal**:
   - Every API call is wrapped in `_execute_with_auth_retry()`.
   - If Angel One returns a token expiration code (`AG8001`, `AG8002`, `AG8003`, `AB1004`), the client automatically regenerates a new TOTP, re-authenticates, and transparently retries the failed request.

---

## 3. Workflow 2: Macro Screening & Dynamic Watchlist Generation

The application does not trade a static list of stocks. It dynamically screens the **210 liquid NSE F&O equities** to select the top 20 cleanest trending stocks for the day.

```
210 F&O Universe
       │
       ▼
[Gate 1] Price Floor: LTP >= ₹150 (eliminates penny stocks)
       │
       ▼
[Gate 2] Institutional Liquidity: 20-Day ADT >= ₹40 Crore
       │
       ▼
[Gate 3] Intraday Expansion: Daily ATR >= 1.5%
       │
       ▼
[Gate 4] Trend Directionality: Kaufman Efficiency Ratio (KER 20D) >= 0.35
       │
       ▼
[Gate 5] Blacklist Filter: Excludes chronic whipsaw names (PGEL, TIINDIA, RECLTD)
       │
       ▼
Calculate Trend-Efficiency Score:
Score = (25 x KER) + (20 x DirEff) + (1.0 x Range%) + (1.0 x Body%) + (0.5 x NetMove)
       │
       ▼
Top 20 Ranked Stocks ──► Dispatched to Active Trading Watchlist
```

### Re-Screening Rhythms
- **Initial Run**: Runs at application startup.
- **30-Minute Scheduled Re-Screening**: Re-evaluates universe ranking at **09:30, 10:00, 10:30, 11:00, 11:30, 12:00, 12:30, 13:00, 13:30, 14:00, 14:30 IST**.
- **Active Position Preservation**: When re-screening completes, any symbol that currently has an open active trade is strictly retained in the watchlist, while idle slots are rotated into newly emerging trend leaders.

---

## 4. Workflow 3: Market Regime Classification & Structural Gating

Before any strategy signal is processed, the system classifies the macro price regime of the underlying stock ([backend/market_regime.py](file:///home/gokul/Desktop/angelone-agenti/backend/market_regime.py)).

### Quantitative Regime Matrix

| Market Regime | Technical Formulation | Permitted Setups | Prohibited Setups |
| :--- | :--- | :--- | :--- |
| **`TRENDING_BULL`** | $\text{Close} > 50\text{ EMA}$, $\text{ADX} \ge 20$, $+DI > -DI$, $\text{KER} \ge 0.35$ | BUY Breakouts, BUY Trend Continuation | Counter-trend SELL shorts |
| **`TRENDING_BEAR`** | $\text{Close} < 50\text{ EMA}$, $\text{ADX} \ge 20$, $-DI > +DI$, $\text{KER} \ge 0.35$ | SELL Breakouts, SELL Trend Continuation | Counter-trend BUY longs |
| **`CHOPPY_RANGE`** | $\text{ADX} < 20$ OR $\text{KER} < 0.35$ OR Bollinger Band Squeeze $< 1.8\%$ | Oscillators, Mean Reversion | **ALL Breakouts & Trend entries BLOCKED** |
| **`VOLATILE_EXPANSION`**| Outsized candle expansion / transitional volatility | High-conviction structural volume setups | Low-liquidity breakout chases |

**The Choppy Range Circuit Breaker**: Over 70% of algorithmic drawdowns in retail trading happen when breakout strategies fire into sideways consolidations. When `CHOPPY_RANGE` is detected, the engine suppresses all breakout entries, completely eliminating whipsaw fee churn.

---

## 5. Workflow 4: Real-Time Scanning & Strategy Confluence Gate

The engine runs a **60-second slow loop** that evaluates 5-minute candle charts across the active watchlist.

```
60-Second Loop Triggered
          │
          ▼
Fetch latest 5m candles (optimized 150-bar rolling slice)
          │
          ▼
Run Enabled Strategies & Tag Signals with Strategy ID
          │
          ▼
Group Signals by Direction (BUY vs SELL)
          │
          ▼
Map Signals to 8 Signal Families (1 Vote Per Family Rule)
          │
          ▼
Check Confluence Gates:
  1. Confluence Score >= 3 Independent Families
  2. 50-EMA Trend Alignment (BUY >= 50 EMA, SELL <= 50 EMA)
  3. Market Regime allows the direction
  4. Planned Target Geometry >= 1:2.0 Risk-Reward
          │
          ├─► Any check fails ──► Signal Rejected
          │
          └─► All checks pass ──► Dispatched to Pre-Trade Friction Guard
```

### The 1-Vote-Per-Family Rule
To prevent redundant indicators from faking consensus, strategies are grouped into 8 families:
1. **Breakout**: Donchian Breakout, Keltner Channel Breakout, Bollinger Band Breakout.
2. **Structure**: Volume Delta Divergence.
3. **Volume**: Chaikin Money Flow (CMF) Institutional Accumulation.
4. **Intraday**: VWAP Bounce, Opening Range Breakout.
5. **Reversal**: Liquidity Grab Reversal, Gap Fill.
6. **Trend**: EMA Crossover, Supertrend, Parabolic SAR, ADX Momentum.
7. **Momentum**: MACD Histogram Cross, RSI Momentum, TSI Cross.
8. **Oscillator**: Stochastic, StocRSI, CCI, Williams %R, MFI Exhaustion.

*Rule*: Even if Donchian, Keltner, and Bollinger all trigger BUY simultaneously, the `Breakout` family receives **exactly ONE vote**. A trade setup must have at least 3 distinct families (e.g., Breakout + Volume + Structure) agreeing in direction.

---

## 6. Workflow 5: Pre-Trade Statutory Friction Defense

Statutory friction in Indian intraday equity trading (Brokerage + STT + Turnover fees + Stamp duty + SEBI + GST) can destroy positive gross expectancy. The system models the exact regulatory tariff:

$$\text{Brokerage per leg} = \max(₹5.0, \min(₹20.0, 0.1\% \times \text{Turnover}))$$

### Complete Statutory Breakdown
* **Brokerage**: Lower of ₹20 or 0.1% per executed order (min ₹5).
* **Securities Transaction Tax (STT)**: 0.025% on sell side.
* **Exchange Turnover Fee (NSE)**: 0.00297% of round-trip turnover (SEBI True-to-Label).
* **Stamp Duty**: 0.003% on buy side.
* **SEBI Charges**: ₹10 per crore (0.0001%).
* **GST**: 18% on (Brokerage + Exchange Fee + SEBI Fee).

### The Pre-Trade Friction Guard
Before an order is submitted:
1. The engine queries Angel One's live `estimateCharges` API (or its sub-millisecond local tariff fallback) to calculate the exact round-trip friction in rupees.
2. It evaluates the trade's expected gross payoff:
   $$\text{Expected Gross Payoff} = | \text{TargetPrice} - \text{EntryPrice} | \times \text{Quantity}$$
3. **The Gating Rule**:
   $$\mathbf{\text{Expected Gross Payoff} \ge 3.5 \times \text{Estimated Total Friction}}$$
4. If a setup's target profit cannot cover at least **3.5 times the exchange charges**, the trade is rejected pre-trade.

---

## 7. Workflow 6: 1R Position Sizing & Two-Legged Order Execution

```
Candidate Signal Cleared Friction Guard
                 │
                 ▼
Compute 1R Quantity:
  Per-Share Risk = | EntryPrice - StopLoss |
  Raw Qty = floor(Risk Budget ₹500 / Per-Share Risk)
  Max Qty = floor(Margin Ceiling ₹4,000 x 5.0 Leverage / EntryPrice)
  Qty = max(1, min(Raw Qty, Max Qty))
                 │
                 ▼
Submit Leg 1: LIMIT Pullback Order at Value Level
                  • Entry = max(VWAP, EMA20, BreakoutLevel) for BUY (min for SELL)
                  │
                  ├─► Sits in pending_orders queue
                  │         │
                  │         ├─► Unfilled after 15s ──► smart_api_client.cancel_order() (prevents stale adverse fills)
                  │         │
                  │         └─► Fully Executed Fill
                  │                   │
                  │                   ▼
                  │             Submit Leg 2: Native STOPLOSS_LIMIT Order on Angel One
                  │             • Buffered SL = Structural Low - 0.5 x ATR(14)
                  │             • Trigger = StopLoss
                  │             • Limit   = StopLoss x 0.99 (BUY) / 1.01 (SELL)
                 │                   │
                 ▼                   ▼
       Persist Active Trade to ~/.smartapi-agentic-trading/config.json
```

### Why Native Exchange Stop-Loss Orders Matter
Many retail bots maintain stop losses purely in local software memory. If the user's internet drops, power fails, or the computer sleeps, the trade runs unhedged.  
This engine places a **native exchange-side `STOPLOSS_LIMIT` order directly on Angel One's servers** the instant the entry executes. Even if the desktop computer is turned off, the broker's matching engine guarantees stop-loss execution.

---

## 8. Workflow 7: Active Trade Monitoring & Dynamic Exits

Once inside an active position, the engine's **5-second fast loop** monitors live prices and manages exits through 5 distinct mechanisms:

```
Active Trade Monitored Every 5s
               │
               ├─► 1. Hard SL Triggered on Exchange ──► Trade Closed (-1.0R Loss)
               │
               ├─► 2. Price Reaches Target 1 (+1.2R) ──► Front-Loaded Partial Profit Booking:
               │                                         • Exit 50% Quantity at Limit
               │                                         • Atomically modify existing Exchange SL to
               │                                           remaining 50% Qty & Breakeven + RoundTripFriction
               │                                           via Angel One modify_order() (Zero-gap)
               │                                         • Emergency Fallback: If modify fails, trigger
               │                                           immediate emergency market exit
               │
               ├─► 3. Price Advances >= +1.5R Cushion ─► ATR / 20-EMA Trailing Ratchet:
               │                                         • Trail 2.2 x ATR behind High-Water Mark
               │                                         • Modify exchange SL via modify_order()
               │
               ├─► 4. Thesis & Idle Circuit Breaker ──► • Opposing signals >= 2: Immediate Exit
               │                                         • Stagnant trade held >= 20m without +0.5R: Exit at market
               │                                         • 0 supporting signals after 15m in loss: Exit
               │
               ├─► 5. Pre-Square-Off Cutoff (15:00) ───► No new intraday entry order submissions
               │
               └─► 6. Clock Reaches 15:15 IST ─────────► Mandatory EOD Square-Off
```

### Detailed Exit Mechanisms:
1. **Target 1 Front-Loaded Booking & Breakeven Friction Guard**:
   - Once price reaches $+1.2R$ and expected profit covers round-trip friction, 50% of the position is booked.
   - **Breakeven + Friction Protection**: The remaining 50% stop loss is ratcheted to $\text{EntryPrice} \pm \text{RoundTripFrictionPerShare}$, guaranteeing that a breakeven exit produces non-negative net P&L after all statutory taxes and fees.
   - **Atomic Modification & Emergency Close**: Uses SmartAPI `modify_order()` to atomically update quantity and trigger price. If modification fails, the system immediately triggers an emergency market close to prevent unhedged market exposure.
2. **Idle Trade Circuit Breaker (20 Minutes)**:
   - If an active position fails to advance by at least $+0.5R$ within 20 minutes, it is closed at market to eliminate stagnation and capital drag during intraday chop.
3. **Continuous Intraday Execution (09:30–15:00 IST)**:
   - Midday lockout blocks have been removed. Technical confluence, market regime classification, and 1:2 R:R geometry protect entries continuously without arbitrary midday freezes.
4. **Relaxed ATR / 20-EMA Trailing SL**:
   - Only activates after price moves at least $+1.5R$ in profit, trailing $2.2 \times \text{ATR}$ behind the high-water mark via `modify_order()`.

---

## 9. Workflow 8: End-of-Day Square-Off & Post-Market Reconciliation

```
15:00 IST ──► Intraday Entry Gate Closes (No new orders allowed)
                   │
                   ▼
15:15 IST ──► Mandatory Auto Square-Off Initiated:
              1. Cancel all resting exchange STOPLOSS_LIMIT orders
              2. Place MARKET exit orders for all remaining open positions
                   │
                   ▼
              Query Completed Orders & Brokerage from Angel One
                   │
                   ▼
              Reconcile Gross P&L, Net P&L, and Statutory Charges
                   │
                   ▼
              Dispatch EOD Markdown Summary to Telegram Bot & UI
```

### Circuit Breaker Enforcements
* **Daily Trade Limit**: Maximum **8 trades per day** across the portfolio.
* **Max Daily Loss Limit**: Hard **₹800 loss cap**. If hit at any point during the day, the engine calls `square_off_all()` and halts trading for the day.
* **Max Concurrent Positions**: Capped at **4 simultaneous open trades**.

---

## 10. Workflow 9: Remote Surveillance & Emergency Telegram Controls

The application integrates an asynchronous **2-way Telegram Bot** ([backend/telegram_bot.py](file:///home/gokul/Desktop/angelone-agenti/backend/telegram_bot.py)) allowing remote monitoring and emergency intervention from a smartphone:

```
Trader Smartphone ──► Telegram Cloud ──► Inbound Polling Thread (telegram_bot.py)
                                                    │
                                                    ▼
                                         Authorized Chat ID Check
                                                    │
                                                    ▼
                                         Execute Engine Action:
                                         • /status     (Current P&L & positions)
                                         • /positions  (Detailed active trade view)
                                         • /squareoff  (Emergency panic button)
                                         • /stop       (Halt automated trading)
                                         • /start      (Resume automated trading)
```

### Outbound Alert Dispatcher
* **Trade Execution**: Alerts with entry price, quantity, stop loss, and target.
* **Partial Booking**: Notifies when 50% profit is booked at $+2.0R$ and stop loss is moved to breakeven.
* **Trade Exits**: Sends realized gross P&L, statutory charges, and net P&L.
* **EOD Session Summary**: Full ledger breakdown at 15:15 IST.
