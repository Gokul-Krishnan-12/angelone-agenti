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
from typing import List, Optional

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


DEFAULT_BLACKLIST: List[str] = ["PGEL", "TIINDIA", "RECLTD"]


def screen_top_momentum_fno(
    period: str = "30d",
    top_n: int = 20,
    min_price: float = 0.0,
    max_price: float = 100_000.0,
    min_daily_volume: int = 0,
    blacklist: Optional[List[str]] = None,
    min_ker: float = 0.35,
) -> list[str]:
    """Rank F&O stocks by realized intraday range, directional velocity, and net trend.

    Excludes low-efficiency regime stocks via Kaufman Efficiency Ratio (KER >= 0.35).
    """
    import pandas as pd
    import yfinance as yf

    from ..fno_universe import get_fno_universe
    from ..screener import calculate_kaufman_efficiency_ratio

    active_blacklist = set(blacklist if blacklist else DEFAULT_BLACKLIST)

    fno = [s for s in get_fno_universe() if s not in active_blacklist]
    print(f"\n[Screener] Screening {len(fno)} F&O stocks (KER gate: >= {min_ker})...")
    tickers = [f"{s}.NS" for s in fno]

    daily_period = period if period in ("30d", "60d", "90d") else "60d"
    try:
        df = yf.download(
            tickers=tickers, period=daily_period, interval="1d", progress=False
        )
    except Exception as e:
        print(
            f"[Screener] Batch fetch failed: {e}. Falling back to default F&O selection."
        )
        return fno[:top_n]

    scores = []
    for s in fno:
        if s in active_blacklist:
            continue
        try:
            sub = pd.DataFrame(
                {
                    "high": df["High"][f"{s}.NS"],
                    "low": df["Low"][f"{s}.NS"],
                    "close": df["Close"][f"{s}.NS"],
                    "open": df["Open"][f"{s}.NS"],
                    "volume": df["Volume"][f"{s}.NS"],
                }
            ).dropna()
            if len(sub) < 10:
                continue

            mean_p = float(sub["close"].mean())
            avg_vol = float(sub["volume"].mean())

            if min_price > 0 and mean_p < min_price:
                continue
            if max_price < 100_000.0 and mean_p > max_price:
                continue
            if min_daily_volume > 0 and avg_vol < min_daily_volume:
                continue

            ker = calculate_kaufman_efficiency_ratio(
                sub["close"], period=min(20, len(sub) - 1)
            )
            if min_ker > 0.0 and ker < min_ker:
                continue

            range_pct = float(((sub["high"] - sub["low"]) / sub["close"] * 100).mean())
            body_pct = float(
                (abs(sub["close"] - sub["open"]) / sub["open"] * 100).mean()
            )
            net_move = float(
                abs(sub["close"].iloc[-1] - sub["close"].iloc[0])
                / sub["close"].iloc[0]
                * 100
            )

            # Trend efficiency (net directional move vs total cumulative range)
            tot_range = float((sub["high"] - sub["low"]).sum())
            dir_efficiency = abs(sub["close"].iloc[-1] - sub["close"].iloc[0]) / (
                tot_range + 1e-6
            )

            score = (
                (ker * 25.0)
                + (dir_efficiency * 20.0)
                + (range_pct * 1.0)
                + (body_pct * 1.0)
                + (net_move * 0.5)
            )
            scores.append((s, score))
        except Exception:
            pass

    if not scores:
        return fno[:top_n]

    scores.sort(key=lambda x: x[1], reverse=True)
    top_symbols = [s for s, _ in scores[:top_n]]
    print(
        f"[Screener] Top {top_n} Quality F&O momentum symbols: {', '.join(top_symbols)}"
    )
    return top_symbols


def main():
    parser = argparse.ArgumentParser(description="Agentic Trading Backtest Runner")
    parser.add_argument(
        "--interval",
        choices=["5m", "15m", "1h", "1d"],
        default="15m",
        help="Candle interval (default: 15m)",
    )
    parser.add_argument(
        "--period",
        default="30d",
        help="Data period: 30d, 60d, 6mo, 1y (default: 30d)",
    )
    parser.add_argument(
        "--universe",
        choices=["fno", "nifty50", "short"],
        default="fno",
        help="Stock universe to screen (default: fno)",
    )
    parser.add_argument(
        "--top-momentum",
        type=int,
        default=20,
        help="Number of top momentum stocks to select (default: 20)",
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=None,
        help="Custom NSE symbols to test (overrides universe)",
    )
    parser.add_argument(
        "--output",
        default="backtest_report.md",
        help="Output markdown report path (default: backtest_report.md)",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=20000.0,
        help="Capital allocated per trade in INR (default: 20000.0)",
    )

    parser.add_argument(
        "--confluence",
        type=int,
        default=3,
        help="Minimum confluence score (default: 3)",
    )
    parser.add_argument(
        "--min-rr",
        type=float,
        default=2.0,
        help="Minimum R:R ratio gate (default: 2.0)",
    )
    parser.add_argument(
        "--trailing-atr",
        type=float,
        default=2.0,
        help="Trailing stop loss multiplier (default: 2.0 × ATR)",
    )
    parser.add_argument(
        "--trail-after-r",
        type=float,
        default=1.0,
        help="Activate trailing SL only after reaching N × R profit (default: 1.0)",
    )
    parser.add_argument(
        "--min-sl-pct",
        type=float,
        default=1.0,
        help="Minimum stop-loss width percent (default: 1.0%%)",
    )
    parser.add_argument(
        "--no-trend-filter",
        action="store_true",
        help="Disable the 50-EMA trend alignment quality filter",
    )
    parser.add_argument(
        "--disabled-strategies",
        nargs="*",
        default=None,
        help="Optional list of strategy IDs to disable",
    )
    parser.add_argument(
        "--min-price",
        type=float,
        default=100.0,
        help="Quality filter: minimum nominal stock price (default: 100.0)",
    )
    parser.add_argument(
        "--max-price",
        type=float,
        default=3000.0,
        help="Quality filter: maximum nominal stock price (default: 3000.0)",
    )
    parser.add_argument(
        "--min-vol",
        type=int,
        default=0,
        help="Quality filter: minimum average daily volume (default: 0)",
    )
    parser.add_argument(
        "--min-ker",
        type=float,
        default=0.35,
        help="Minimum Kaufman Efficiency Ratio gate (default: 0.35)",
    )
    parser.add_argument(
        "--blacklist",
        nargs="*",
        default=None,
        help="Symbols to exclude from trading (default: PGEL, TIINDIA, RECLTD, plus dynamic KER)",
    )

    args = parser.parse_args()

    # Symbol selection
    if args.symbols:
        blacklist = set(args.blacklist or DEFAULT_BLACKLIST)
        symbols = [s for s in args.symbols if s not in blacklist]
    elif args.universe == "fno":
        symbols = screen_top_momentum_fno(
            period=args.period,
            top_n=args.top_momentum,
            min_price=args.min_price,
            max_price=args.max_price,
            min_daily_volume=args.min_vol,
            blacklist=args.blacklist,
            min_ker=args.min_ker,
        )
    elif args.universe == "nifty50":
        symbols = NIFTY_50_SUBSET[: args.top_momentum]
    else:
        symbols = SHORT_SYMBOLS

    print("=" * 70)
    print("  Kite / SmartAPI Agentic Trading — Backtest Engine")
    print("=" * 70)
    print(f"  Interval     : {args.interval}")
    print(f"  Period       : {args.period}")
    print(f"  Capital/Trade: ₹{args.capital:,.0f}")
    print(f"  Universe     : {args.universe} (top {len(symbols)} symbols)")
    print(
        f"  Symbols      : {', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''}"
    )
    print(f"  Gate         : confluence ≥ {args.confluence}, R:R ≥ {args.min_rr}")
    print(
        f"  Quality Gate : min SL width ≥ {args.min_sl_pct}%, 50-EMA trend filter {'OFF' if args.no_trend_filter else 'ON'}"
    )
    print(
        f"  Trailing SL  : {args.trailing_atr} × ATR (after +{args.trail_after_r}R profit cushion)"
    )
    print("=" * 70)

    # ── Step 1: Fetch data ─────────────────────────────────────────────
    from .data_fetcher import fetch_candles

    print(
        f"\n[Step 1/3] Downloading historical data for {len(symbols)} symbols from Yahoo Finance..."
    )
    symbol_dfs = {}
    for sym in symbols:
        print(f"  Fetching {sym}... ", end="", flush=True)
        df = fetch_candles(sym, period=args.period, interval=args.interval)
        if df.empty:
            print("FAILED (skipping)")
        else:
            symbol_dfs[sym] = df
            print(f"OK ({len(df)} bars)")
        time.sleep(0.3)  # rate-limit yfinance

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
        capital_per_trade=args.capital,
        trailing_sl_multiplier=args.trailing_atr,
        min_bars=60,
        trail_after_r=args.trail_after_r,
        trend_aligned=not args.no_trend_filter,
        min_sl_pct=args.min_sl_pct,
        disabled_strategies=args.disabled_strategies,
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
        capital=args.capital,
        confluence=args.confluence,
        min_rr=args.min_rr,
    )


if __name__ == "__main__":
    main()
