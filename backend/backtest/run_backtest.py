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
from pathlib import Path
from typing import List, Optional

# Ensure workspace root is on sys.path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

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

SHORT_SYMBOLS = ["MAZDOCK", "BDL", "KEI", "GODREJPROP", "KPITTECH"]


try:
    from ..screener import DEFAULT_BLACKLIST as SCREENER_BLACKLIST
except (ImportError, ValueError):
    from backend.screener import DEFAULT_BLACKLIST as SCREENER_BLACKLIST

DEFAULT_BLACKLIST: List[str] = sorted(list(set(SCREENER_BLACKLIST)))


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
    try:
        from ..config import ConfigManager

        _cfg = ConfigManager().get_risk_config()
    except Exception:
        _cfg = {}

    default_capital = float(_cfg.get("maxCapitalPerTrade", 8000) * 5)
    default_confluence = int(_cfg.get("minConfluenceScore", 2))
    default_confluence_trending = int(_cfg.get("minConfluenceScoreTrending", 2))
    default_min_rr = float(_cfg.get("minRiskReward", 1.8))
    default_trailing_atr = float(_cfg.get("trailingSlAtrMultiplier", 2.2))
    default_trail_after_r = float(_cfg.get("trailingSlProfitCushionR", 1.5))
    default_min_sl_pct = float(_cfg.get("minStopLossPercent", 1.0))
    default_max_sl_pct = float(_cfg.get("maxStopLossPercent", 2.4))
    default_max_daily_trades = int(_cfg.get("maxDailyTrades", 8))

    parser = argparse.ArgumentParser(description="Agentic Trading Backtest Runner")
    parser.add_argument(
        "--interval",
        choices=["5m", "15m", "1h", "1d"],
        default="15m",
        help="Candle interval (default: 15m)",
    )
    parser.add_argument(
        "--period",
        default="60d",
        help="Data period: 30d, 60d, 6mo, 1y (default: 60d)",
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
        default=25,
        help="Number of top momentum stocks to select (default: 25)",
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
        default=default_capital,
        help=f"Capital allocated per trade in INR (default: {default_capital})",
    )

    parser.add_argument(
        "--confluence",
        type=int,
        default=default_confluence,
        help=f"Minimum confluence score (default: {default_confluence})",
    )
    parser.add_argument(
        "--confluence-trending",
        type=int,
        default=default_confluence_trending,
        help=f"Minimum confluence score in trending regime (default: {default_confluence_trending})",
    )
    parser.add_argument(
        "--min-rr",
        type=float,
        default=default_min_rr,
        help=f"Minimum R:R ratio gate (default: {default_min_rr})",
    )
    parser.add_argument(
        "--trailing-atr",
        type=float,
        default=default_trailing_atr,
        help=f"Trailing stop loss multiplier (default: {default_trailing_atr} × ATR)",
    )
    parser.add_argument(
        "--trail-after-r",
        type=float,
        default=default_trail_after_r,
        help=f"Activate trailing SL only after reaching N × R profit (default: {default_trail_after_r})",
    )
    parser.add_argument(
        "--min-sl-pct",
        type=float,
        default=default_min_sl_pct,
        help=f"Minimum stop-loss width percent (default: {default_min_sl_pct}%%)",
    )
    parser.add_argument(
        "--max-sl-pct",
        type=float,
        default=default_max_sl_pct,
        help=f"Maximum stop-loss width percent cap (default: {default_max_sl_pct}%%)",
    )
    parser.add_argument(
        "--max-daily-trades",
        type=int,
        default=default_max_daily_trades,
        help=f"Maximum trades executed per day across portfolio (default: {default_max_daily_trades})",
    )
    parser.add_argument(
        "--no-trend-filter",
        action="store_true",
        help="Disable the 50-EMA trend alignment quality filter",
    )
    parser.add_argument(
        "--no-partial-booking",
        action="store_true",
        help="Disable partial booking (let runners ride with trailing SL to target)",
    )
    parser.add_argument(
        "--no-pullback-entry",
        action="store_true",
        help="Disable pullback limit entry (use breakout candle open entry)",
    )
    parser.add_argument(
        "--stagnation-mins",
        type=float,
        default=None,
        help="Stagnation timeout in minutes (default: auto 35m for 5m, 75m for 15m)",
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
    try:
        from .engine import BacktestEngine
    except (ImportError, ValueError):
        from backend.backtest.engine import BacktestEngine

    print("\n[Step 2/3] Running walk-forward backtest...")
    t0 = time.time()
    engine = BacktestEngine(
        min_confluence=args.confluence,
        min_confluence_trending=args.confluence_trending,
        min_rr=args.min_rr,
        capital_per_trade=args.capital,
        trailing_sl_multiplier=args.trailing_atr,
        min_bars=60,
        trail_after_r=args.trail_after_r,
        trend_aligned=not args.no_trend_filter,
        min_sl_pct=args.min_sl_pct,
        max_sl_pct=args.max_sl_pct,
        max_trades_per_day=args.max_daily_trades,
        disabled_strategies=args.disabled_strategies,
        partial_booking_enabled=not args.no_partial_booking,
        pullback_entry_enabled=not args.no_pullback_entry,
        interval=args.interval,
        stagnation_timeout_mins=args.stagnation_mins,
    )
    trades = engine.run(symbol_dfs)
    elapsed = time.time() - t0

    print(f"\n  Backtest complete in {elapsed:.1f}s. Total trades: {len(trades)}")

    if not trades:
        print("\n[Warning] No trades were generated. Strategies may be too selective")
        print("          for the chosen interval/period, or data is insufficient.")
        sys.exit(0)

    # ── Step 3: Report ─────────────────────────────────────────────────
    try:
        from .reporter import generate_report
    except (ImportError, ValueError):
        from backend.backtest.reporter import generate_report

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
