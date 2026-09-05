"""
Backtest reporter — computes statistics and writes a markdown report.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import List

from .engine import BacktestTrade


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    return round(a / b, 4) if b else default


def generate_report(
    trades: List[BacktestTrade],
    symbols: List[str],
    interval: str,
    period: str,
    output_path: str | None = None,
) -> dict:
    """
    Compute backtest statistics and produce a markdown report.

    Returns a dict with all metrics (also printed to stdout).
    """
    if not trades:
        print("[Reporter] No trades to report.")
        return {}

    # ── Basic counts ─────────────────────────────────────────────────
    n = len(trades)
    wins = [t for t in trades if t.pnl_pct > 0]
    losses = [t for t in trades if t.pnl_pct <= 0]
    win_rate = len(wins) / n * 100
    avg_win_pct = statistics.mean(t.pnl_pct for t in wins) if wins else 0
    avg_loss_pct = statistics.mean(t.pnl_pct for t in losses) if losses else 0

    # ── P&L ─────────────────────────────────────────────────────────
    total_pnl_rs = sum(t.pnl_rs for t in trades)
    gross_profit = sum(t.pnl_rs for t in wins)
    gross_loss = abs(sum(t.pnl_rs for t in losses))
    profit_factor = _safe_div(gross_profit, gross_loss, default=float("inf"))

    # ── Expectancy (per trade in ₹) ───────────────────────────────────
    expectancy = _safe_div(total_pnl_rs, n)

    # ── R:R ──────────────────────────────────────────────────────────
    avg_rr = statistics.mean(t.rr_achieved for t in trades)
    median_rr = statistics.median(t.rr_achieved for t in trades)

    # ── Drawdown (running) ────────────────────────────────────────────
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    dd_series = []
    for t in trades:
        equity += t.pnl_rs
        peak = max(peak, equity)
        dd = peak - equity
        dd_series.append(dd)
        max_dd = max(max_dd, dd)

    # ── Sharpe (simplified, assumes 0 risk-free) ─────────────────────
    returns = [t.pnl_pct for t in trades]
    if len(returns) > 1:
        mean_r = statistics.mean(returns)
        std_r = statistics.stdev(returns)
        sharpe = round(mean_r / std_r, 2) if std_r > 0 else 0.0
    else:
        sharpe = 0.0

    # ── Exit reasons ──────────────────────────────────────────────────
    exit_counts: dict = defaultdict(int)
    for t in trades:
        exit_counts[t.exit_reason] += 1

    # ── Per-strategy contribution ─────────────────────────────────────
    strat_stats: dict = defaultdict(lambda: {"wins": 0, "losses": 0, "pnl": 0.0})
    for t in trades:
        for strat in t.strategies_voting:
            strat_stats[strat]["pnl"] += t.pnl_rs
            if t.pnl_pct > 0:
                strat_stats[strat]["wins"] += 1
            else:
                strat_stats[strat]["losses"] += 1

    # ── Per-symbol breakdown ──────────────────────────────────────────
    sym_stats: dict = defaultdict(lambda: {"trades": 0, "pnl": 0.0, "wins": 0})
    for t in trades:
        sym_stats[t.symbol]["trades"] += 1
        sym_stats[t.symbol]["pnl"] += t.pnl_rs
        if t.pnl_pct > 0:
            sym_stats[t.symbol]["wins"] += 1

    # ── Confluent family breakdown ────────────────────────────────────
    family_stats: dict = defaultdict(lambda: {"trades": 0, "pnl": 0.0})
    for t in trades:
        for fam in t.families_voting:
            family_stats[fam]["trades"] += 1
            family_stats[fam]["pnl"] += t.pnl_rs

    # ── Build report ──────────────────────────────────────────────────
    best_trade = max(trades, key=lambda t: t.pnl_pct)
    worst_trade = min(trades, key=lambda t: t.pnl_pct)
    avg_bars = statistics.mean(t.bars_held for t in trades)
    trailing_sl_exits = exit_counts.get("TRAILING_SL", 0)

    report_lines = [
        "# Backtest Report",
        "",
        f"**Symbols tested:** {', '.join(symbols)}  ",
        f"**Period:** {period}  |  **Interval:** {interval}  ",
        "**Strategies:** 21 (with 2-family confluence gate, min R:R 1.8)  ",
        "**ATR Trailing SL:** enabled (1.5 × ATR)  ",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Trades | **{n}** |",
        f"| Win Rate | **{win_rate:.1f}%** |",
        f"| Profit Factor | **{profit_factor:.2f}** |",
        f"| Total P&L | **₹{total_pnl_rs:,.0f}** (on ₹10,000/trade) |",
        f"| Expectancy (per trade) | ₹{expectancy:,.0f} |",
        f"| Avg Win | +{avg_win_pct:.2f}% |",
        f"| Avg Loss | {avg_loss_pct:.2f}% |",
        f"| Avg R:R Achieved | {avg_rr:.2f} |",
        f"| Median R:R Achieved | {median_rr:.2f} |",
        f"| Max Drawdown | ₹{max_dd:,.0f} |",
        f"| Sharpe Ratio | {sharpe:.2f} |",
        f"| Avg Bars Held | {avg_bars:.1f} |",
        f"| Trailing SL Exits | {trailing_sl_exits} ({trailing_sl_exits / n * 100:.0f}% of trades) |",
        "",
        "---",
        "",
        "## Exit Breakdown",
        "",
        "| Exit Reason | Count | % |",
        "|-------------|-------|---|",
    ]
    for reason, count in sorted(exit_counts.items(), key=lambda x: -x[1]):
        report_lines.append(f"| {reason} | {count} | {count / n * 100:.0f}% |")

    report_lines += [
        "",
        "---",
        "",
        "## Best & Worst Trades",
        "",
        f"**Best:** {best_trade.symbol} {best_trade.direction}  "
        f"Entry ₹{best_trade.entry_price} → Exit ₹{best_trade.exit_price}  "
        f"P&L **+{best_trade.pnl_pct:.2f}%**  "
        f"Exit: {best_trade.exit_reason}",
        "",
        f"**Worst:** {worst_trade.symbol} {worst_trade.direction}  "
        f"Entry ₹{worst_trade.entry_price} → Exit ₹{worst_trade.exit_price}  "
        f"P&L **{worst_trade.pnl_pct:.2f}%**  "
        f"Exit: {worst_trade.exit_reason}",
        "",
        "---",
        "",
        "## Per-Symbol Breakdown",
        "",
        "| Symbol | Trades | Win Rate | P&L (₹) |",
        "|--------|--------|----------|---------|",
    ]
    for sym in sorted(sym_stats, key=lambda s: -sym_stats[s]["pnl"]):
        s = sym_stats[sym]
        wr = s["wins"] / s["trades"] * 100 if s["trades"] else 0
        report_lines.append(f"| {sym} | {s['trades']} | {wr:.0f}% | ₹{s['pnl']:,.0f} |")

    report_lines += [
        "",
        "---",
        "",
        "## Signal Family Contribution",
        "",
        "| Family | Trades Involved | P&L (₹) |",
        "|--------|-----------------|---------|",
    ]
    for fam in sorted(family_stats, key=lambda f: -family_stats[f]["pnl"]):
        f = family_stats[fam]
        report_lines.append(f"| {fam} | {f['trades']} | ₹{f['pnl']:,.0f} |")

    report_lines += [
        "",
        "---",
        "",
        "## Strategy Contribution",
        "",
        "| Strategy | Wins | Losses | P&L (₹) |",
        "|----------|------|--------|---------|",
    ]
    for strat in sorted(strat_stats, key=lambda s: -strat_stats[s]["pnl"]):
        s = strat_stats[strat]
        report_lines.append(
            f"| {strat} | {s['wins']} | {s['losses']} | ₹{s['pnl']:,.0f} |"
        )

    report_lines += [
        "",
        "---",
        "",
        "## Interpretation Notes",
        "",
        "> [!NOTE]",
        "> This backtest simulates entry at the **next bar's open** after a signal fires.",
        "> Slippage, brokerage (₹20/order), STT, and exchange fees are **NOT deducted**.",
        "> Add ~₹50–80 per round-trip to get realistic net P&L.",
        "> 5-min VWAP strategies are less accurate on 1-day timeframe (VWAP resets daily).",
        "",
        "> [!IMPORTANT]",
        "> Past performance on historical data does not guarantee future results.",
        "> Always paper-trade first before committing real capital.",
    ]

    report_md = "\n".join(report_lines)

    # Print to stdout
    print("\n" + report_md)

    # Save to file
    if output_path:
        with open(output_path, "w") as f:
            f.write(report_md)
        print(f"\n[Reporter] Report saved to: {output_path}")

    return {
        "n_trades": n,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "total_pnl_rs": total_pnl_rs,
        "expectancy": expectancy,
        "avg_win_pct": avg_win_pct,
        "avg_loss_pct": avg_loss_pct,
        "avg_rr": avg_rr,
        "median_rr": median_rr,
        "max_drawdown": max_dd,
        "sharpe": sharpe,
        "trailing_sl_exits": trailing_sl_exits,
        "exit_counts": dict(exit_counts),
        "sym_stats": dict(sym_stats),
        "strat_stats": dict(strat_stats),
        "family_stats": dict(family_stats),
    }
