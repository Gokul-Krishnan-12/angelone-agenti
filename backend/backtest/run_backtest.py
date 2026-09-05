"""
Backtest runner — CLI entry point.

Usage:
    uv run python -m backend.backtest.run_backtest
    uv run python -m backend.backtest.run_backtest --interval 1d --period 6mo
    uv run python -m backend.backtest.run_backtest --interval 5m --period 60d --symbols RELIANCE TCS INFY

Arguments:
    --interval   Bar size: 5m | 15m | 1h | 1d  (default: 1d)
    --period     Data lookback: 60d | 6mo | 1y   (default: 6mo)
    --symbols    Space-separated NSE symbols      (default: Nifty 50 subset)
    --output     Output markdown file path        (default: backtest_report.md)
"""

from __future__ import annotations

import argparse
import sys
import time

# ── Default symbol list (Nifty 50 liquid names) ──────────────────────────────

NIFTY_50_SUBSET = [
    "RELIANCE",
    "TCS",
    "HDFCBANK",
    "INFY",
    "ICICIBANK",
    "HINDUNILVR",
    "ITC",
    "SBIN",
    "BHARTIARTL",
    "KOTAKBANK",
    "LT",
    "AXISBANK",
    "ASIANPAINT",
    "MARUTI",
    "TITAN",
    "SUNPHARMA",
    "BAJFINANCE",
    "WIPRO",
    "ULTRACEMCO",
    "NESTLEIND",
]

SHORT_SYMBOLS = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK"]


def main():
    parser = argparse.ArgumentParser(description="Agentic Trading Backtest Runner")
    parser.add_argument(
        "--interval",
        choices=["5m", "15m", "1h", "1d"],
        default="1d",
        help="Candle interval (default: 1d)",
    )
    parser.add_argument(
        "--period",
        default="6mo",
        help="Data period: 60d, 6mo, 1y, 2y (default: 6mo)",
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=None,
        help="NSE symbols to test (default: Nifty 50 subset)",
    )
    parser.add_argument(
        "--output",
        default="backtest_report.md",
        help="Output markdown report path (default: backtest_report.md)",
    )
    parser.add_argument(
        "--confluence",
        type=int,
        default=2,
        help="Minimum confluence score (default: 2)",
    )
    parser.add_argument(
        "--min-rr",
        type=float,
        default=1.8,
        help="Minimum R:R ratio gate (default: 1.8)",
    )

    args = parser.parse_args()

    # Symbol selection
    if args.symbols:
        symbols = args.symbols
    elif args.interval in ("5m", "15m"):
        # Short-period intraday: fewer symbols due to yfinance 5-min limits
        symbols = SHORT_SYMBOLS
        if args.period not in ("60d", "30d"):
            print(
                "[Warning] yfinance caps 5m/15m data at 60 days. "
                "Overriding period to '60d'."
            )
            args.period = "60d"
    else:
        symbols = NIFTY_50_SUBSET

    print("=" * 70)
    print("  Kite Agentic Trading — Backtest Engine")
    print("=" * 70)
    print(f"  Interval : {args.interval}")
    print(f"  Period   : {args.period}")
    print(
        f"  Symbols  : {len(symbols)} ({', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''})"
    )
    print(f"  Gate     : confluence ≥ {args.confluence}, R:R ≥ {args.min_rr}")
    print("  Trailing SL : enabled (1.5 × ATR)")
    print("=" * 70)

    # ── Step 1: Fetch data ─────────────────────────────────────────────
    from .data_fetcher import fetch_candles

    print("\n[Step 1/3] Downloading historical data from Yahoo Finance...")
    symbol_dfs = {}
    for sym in symbols:
        print(f"  Fetching {sym}... ", end="", flush=True)
        df = fetch_candles(sym, period=args.period, interval=args.interval)
        if df.empty:
            print("FAILED (skipping)")
        else:
            symbol_dfs[sym] = df
            print(f"OK ({len(df)} bars)")
        time.sleep(0.5)  # rate-limit yfinance

    if not symbol_dfs:
        print("\n[Error] No data fetched. Check internet connection.")
        sys.exit(1)

    print(f"\n  Successfully loaded {len(symbol_dfs)}/{len(symbols)} symbols.")

    # ── Step 2: Run backtest ───────────────────────────────────────────
    from .engine import BacktestEngine

    print("\n[Step 2/3] Running walk-forward backtest...")
    t0 = time.time()
    engine = BacktestEngine(
        min_confluence=args.confluence,
        min_rr=args.min_rr,
        capital_per_trade=10_000.0,
        trailing_sl_multiplier=1.5,
        min_bars=60,
    )
    trades = engine.run(symbol_dfs)
    elapsed = time.time() - t0

    print(f"\n  Backtest complete in {elapsed:.1f}s. Total trades: {len(trades)}")

    if not trades:
        print("\n[Warning] No trades were generated. Strategies may be too selective")
        print("          for the chosen interval/period, or data is insufficient.")
        sys.exit(0)

    # ── Step 3: Report ─────────────────────────────────────────────────
    from .reporter import generate_report

    print("\n[Step 3/3] Generating report...")
    generate_report(
        trades,
        symbols=list(symbol_dfs.keys()),
        interval=args.interval,
        period=args.period,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
