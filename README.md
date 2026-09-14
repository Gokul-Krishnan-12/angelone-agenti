# Angel One SmartAPI Agentic Trading App

An automated, quantitative algorithmic trading application built on top of the **Angel One SmartAPI** (`smartapi-python`). 

The app features a modern Electron/React frontend communicating with a high-performance, multi-threaded Python backend. It acts as an autonomous agent that continuously scans the NIFTY 50 universe (plus custom watchlists) using 20 distinct technical analysis strategies, grouping them by **Confluence** to generate high-probability trade setups.

## 🚀 Features

* **Advanced Confluence UI**: Groups signals by stock and trade direction. Stocks that trigger multiple strategies simultaneously are ranked at the top, allowing you to instantly spot the highest-probability setups.
* **Kaufman Efficiency Ratio (KER) Macro Regime Screener**: Evaluates 20-day daily price efficiency ($\text{KER} \ge 0.28$) pre-market to filter out choppy, mean-reverting stocks while preserving clean momentum runners.
* **Pre-Trade Statutory Friction Guard**: Automatically models and deducts complete Indian regulatory friction (Brokerage ₹20, STT 0.025%, NSE turnover 0.00325%, Stamp Duty 0.003%, SEBI, and 18% GST). Rejects any trade where expected payoff is $< 3.5\times$ estimated friction.
* **Dynamic Quality Universe Gate**: Automatically excludes noisy consolidation traps and false-breakout regimes using the Kaufman Efficiency Ratio (KER) filter and enforces strict volume/liquidity thresholds.
* **Portfolio Trade Cap (Max 8 Trades/Day)**: Chronologically restricts portfolio churn to prevent overtrading and fee erosion.
* **High-Expectancy Alpha Strategies**: 
  * *Volatility & Breakout*: Donchian Breakout, Keltner Channel Breakout, Bollinger Breakout.
  * *Institutional Footprint*: Order Block & Fair Value Gap (FVG), CMF Institutional Flow, Institutional Volume Absorption, Volume Delta Divergence.
  * *Momentum & Trend*: Parabolic SAR, MACD Divergence Cross, Awesome Oscillator, TSI Cross, EMA Crossover, Stochastic RSI.
* **Walk-Forward Backtest Engine**: Built-in vectorized multi-strategy backtester with Yahoo Finance caching, statutory friction modeling, and automated Markdown report generation.
* **Agentic Execution Modes**:
  * **Full Auto**: The agent strictly executes trades automatically based on risk configurations.
  * **Signal + Confirm**: The agent generates setups and targets, but waits for manual 1-click execution.
* **Automated 2FA**: Using `pyotp`, the app automatically computes time-based one-time passwords from your TOTP secret key for headless session creation and persistent background trading.
* **Parallel Scanning**: The Python engine uses intelligent ThreadPool execution to scan the entire market in parallel while respecting SmartAPI rate limits.
* **Local Persistence**: All trade histories, activity logs, and pending signals are securely stored locally across sessions.

## 🛠️ Tech Stack

* **Frontend**: Electron, React 18, TypeScript, Tailwind CSS, Zustand (with local persistence), Vite.
* **Backend**: Python 3, `smartapi-python`, `pyotp`, `pandas`, `ta` (Technical Analysis), custom JSON-RPC bridge.
* **Security**: API keys, Client Codes, MPINs, and TOTP secrets are locally encrypted using `cryptography.fernet` and stored in `~/.smartapi-agentic-trading/config.json`.

## 📦 Prerequisites

1. **Node.js** (v18 or higher recommended)
2. **uv** (latest version recommended; installs Python environments and packages)
3. An active **Angel One Account**
4. An **Angel One SmartAPI** application (API Key from [smartapi.angelone.in](https://smartapi.angelone.in/))

## ⚙️ Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/smartapi-agentic-trading.git
   cd smartapi-agentic-trading
   ```

2. **Install Frontend Dependencies**
   ```bash
   npm install
   ```

3. **Install Backend Dependencies**
   ```bash
   uv sync
   ```

`uv sync` creates the project environment in `.venv` and installs the locked backend dependencies.

## 🚀 Running the App

To start the application in development mode:

```bash
npm run dev
```

On first launch, enter your:
- **API Key**
- **Client Code (User ID)**
- **4-Digit MPIN / Password**
- **TOTP Secret Key** (from your authenticator app setup)

The app will encrypt and save them locally and authenticate headlessly without requiring web redirects.

## 📈 Walk-Forward Backtesting

The repository includes a walk-forward backtesting suite with full statutory Indian friction modeling (Brokerage ₹20, STT 0.025%, NSE turnover 0.00325%, Stamp Duty, SEBI fees, and 18% GST):

```bash
# Run 60-day 15-minute backtest with ₹40k capital and max 8 trades/day cap
uv run python -m backend.backtest.run_backtest \
    --period 60d \
    --interval 15m \
    --capital 40000 \
    --universe fno \
    --top-momentum 15 \
    --output backtest_report.md
```

Options:
- `--capital`: Capital allocated per trade in INR (default: `20000.0`, recommended: `40000.0`).
- `--period`: Lookback period: `30d`, `60d`, `6mo`, `1y` (default: `30d`).
- `--interval`: Bar size: `5m`, `15m`, `1h`, `1d` (default: `15m`).
- `--blacklist`: Symbols to exclude from simulation (default: `SUZLON TIINDIA ICICIGI`).
- `--confluence`: Minimum strategy family agreement gate (default: `2`).
- `--min-rr`: Minimum target risk-reward ratio (default: `1.8`).
- `--trailing-atr`: ATR trailing stop loss multiplier (default: `2.0` after +1.0R cushion).

## 🧪 Running Tests

The backend test suite (`pytest`) covers the trading strategies. The strategy signal calculations are pure functions, so the tests run fully offline without broker credentials or network access:

```bash
uv run pytest
```

## 🎨 Code Style (Python & Frontend)

```bash
uv run ruff check backend/ run_backend.py     # Python lint (PEP 8)
uv run ruff format backend/ run_backend.py    # Python auto-format
npm run lint                                  # Frontend lint
npm run typecheck                             # TypeScript typecheck
```

## 🏗️ Building for Production

```bash
npm run build
npm run dist
```

## ⚠️ Disclaimer

**This software is for educational and research purposes only.** Algorithmic trading involves significant risk of loss. Always test your strategies in a paper-trading environment before deploying real capital. You are solely responsible for any trades executed by this agent.
