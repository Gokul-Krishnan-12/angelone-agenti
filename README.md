# Angel One SmartAPI Agentic Trading App

An automated, quantitative algorithmic trading application built on top of the **Angel One SmartAPI** (`smartapi-python`). 

The app features a modern Electron/React frontend communicating with a high-performance, multi-threaded Python backend. It acts as an autonomous agent that continuously scans the NIFTY 50 universe (plus custom watchlists) using 20 distinct technical analysis strategies, grouping them by **Confluence** to generate high-probability trade setups.

## 🚀 Features

* **Advanced Confluence UI**: Groups signals by stock and trade direction. Stocks that trigger multiple strategies simultaneously are ranked at the top, allowing you to instantly spot the highest-probability setups.
* **20 Quantitative Strategies Built-in**: 
  * *Institutional Footprint*: Institutional Volume Absorption, Order Block & Fair Value Gap (FVG), CMF Institutional Flow.
  * *Trend/Momentum*: Supertrend, ADX Momentum, Parabolic SAR, MACD Cross, TSI Cross, Awesome Oscillator.
  * *Mean Reversion*: RSI Reversal, CCI Reversal, Williams %R, Stochastic Reversal, StochRSI.
  * *Volatility/Breakout*: Bollinger Breakout, Keltner Breakout, Donchian Breakout.
  * *Volume*: VWAP Bounce, MFI Exhaustion.
  * *Moving Averages*: EMA Crossover.
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
