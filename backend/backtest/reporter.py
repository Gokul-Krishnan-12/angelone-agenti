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
    capital: float = 20_000.0,
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

    # ── P&L & Statutory Friction ─────────────────────────────────────
    total_gross_pnl = sum(t.pnl_rs for t in trades)
    total_friction = sum(t.friction_rs for t in trades)
    total_net_pnl = sum(t.net_pnl_rs for t in trades)

    net_wins = [t for t in trades if t.net_pnl_rs > 0]
    net_losses = [t for t in trades if t.net_pnl_rs <= 0]
    net_win_rate = len(net_wins) / n * 100

    net_gross_profit = sum(t.net_pnl_rs for t in net_wins)
    net_gross_loss = abs(sum(t.net_pnl_rs for t in net_losses))
    net_profit_factor = _safe_div(
        net_gross_profit, net_gross_loss, default=float("inf")
    )

    # ── Expectancy (per trade in ₹) ───────────────────────────────────
    expectancy = _safe_div(total_net_pnl, n)

    # ── R:R ──────────────────────────────────────────────────────────
    avg_rr = statistics.mean(t.rr_achieved for t in trades)
    median_rr = statistics.median(t.rr_achieved for t in trades)

    # ── Drawdown (running on Net Equity) ──────────────────────────────
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    dd_series = []
    for t in trades:
        equity += t.net_pnl_rs
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
    strat_stats: dict = defaultdict(
        lambda: {"wins": 0, "losses": 0, "pnl": 0.0, "net_pnl": 0.0}
    )
    for t in trades:
        for strat in t.strategies_voting:
            strat_stats[strat]["pnl"] += t.pnl_rs
            strat_stats[strat]["net_pnl"] += t.net_pnl_rs
            if t.net_pnl_rs > 0:
                strat_stats[strat]["wins"] += 1
            else:
                strat_stats[strat]["losses"] += 1

    # ── Per-symbol breakdown ──────────────────────────────────────────
    sym_stats: dict = defaultdict(
        lambda: {"trades": 0, "pnl": 0.0, "net_pnl": 0.0, "wins": 0}
    )
    for t in trades:
        sym_stats[t.symbol]["trades"] += 1
        sym_stats[t.symbol]["pnl"] += t.pnl_rs
        sym_stats[t.symbol]["net_pnl"] += t.net_pnl_rs
        if t.net_pnl_rs > 0:
            sym_stats[t.symbol]["wins"] += 1

    # ── Confluent family breakdown ────────────────────────────────────
    family_stats: dict = defaultdict(lambda: {"trades": 0, "pnl": 0.0, "net_pnl": 0.0})
    for t in trades:
        for fam in t.families_voting:
            family_stats[fam]["trades"] += 1
            family_stats[fam]["pnl"] += t.pnl_rs
            family_stats[fam]["net_pnl"] += t.net_pnl_rs

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
        "**ATR Trailing SL:** enabled (2.0 × ATR after +1.0R cushion)  ",
        "**Execution Guard:** Statutory Friction Deducted & Max 8 Trades/Day Capped  ",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Trades | **{n}** |",
        "| Daily Trade Cap | **Max 8 trades/day** |",
        f"| Win Rate (Gross) | **{win_rate:.1f}%** |",
        f"| Win Rate (Net of Fees) | **{net_win_rate:.1f}%** |",
        f"| Gross P&L | ₹{total_gross_pnl:,.0f} |",
        f"| Statutory Friction (Brokerage + Taxes) | **-₹{total_friction:,.0f}** |",
        f"| **Realized Net P&L** | **₹{total_net_pnl:,.0f}** (on ₹{capital:,.0f}/trade) |",
        f"| Net Profit Factor | **{net_profit_factor:.2f}** |",
        f"| Net Expectancy (per trade) | **₹{expectancy:,.0f}** |",
        f"| Avg Win | +{avg_win_pct:.2f}% |",
        f"| Avg Loss | {avg_loss_pct:.2f}% |",
        f"| Avg R:R Achieved | {avg_rr:.2f} |",
        f"| Median R:R Achieved | {median_rr:.2f} |",
        f"| Max Drawdown (Net) | ₹{max_dd:,.0f} |",
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
        "## Per-Symbol Breakdown (Net of Brokerage & Taxes)",
        "",
        "| Symbol | Trades | Net Win Rate | Gross P&L (₹) | Net P&L (₹) |",
        "|--------|--------|--------------|---------------|-------------|",
    ]
    for sym in sorted(sym_stats, key=lambda s: -sym_stats[s]["net_pnl"]):
        s = sym_stats[sym]
        wr = s["wins"] / s["trades"] * 100 if s["trades"] else 0
        report_lines.append(
            f"| {sym} | {s['trades']} | {wr:.0f}% | ₹{s['pnl']:,.0f} | **₹{s['net_pnl']:,.0f}** |"
        )

    report_lines += [
        "",
        "---",
        "",
        "## Signal Family Contribution",
        "",
        "| Family | Trades Involved | Net P&L (₹) |",
        "|--------|-----------------|-------------|",
    ]
    for fam in sorted(family_stats, key=lambda f: -family_stats[f]["net_pnl"]):
        f = family_stats[fam]
        report_lines.append(f"| {fam} | {f['trades']} | ₹{f['net_pnl']:,.0f} |")

    report_lines += [
        "",
        "---",
        "",
        "## Strategy Contribution (Net P&L)",
        "",
        "| Strategy | Wins | Losses | Net P&L (₹) |",
        "|----------|------|--------|-------------|",
    ]
    for strat in sorted(strat_stats, key=lambda s: -strat_stats[s]["net_pnl"]):
        s = strat_stats[strat]
        report_lines.append(
            f"| {strat} | {s['wins']} | {s['losses']} | ₹{s['net_pnl']:,.0f} |"
        )

    report_lines += [
        "",
        "---",
        "",
        "## Interpretation Notes",
        "",
        "> [!NOTE]",
        "> This backtest simulates entry at the **next bar's open** after a signal fires.",
        "> Statutory friction (Brokerage ₹20/order, STT 0.025%, NSE turnover 0.00325%, stamp duty, SEBI, 18% GST) is **fully deducted** from all P&L metrics.",
        "> Trades are capped at a maximum of 8 trades per day across the portfolio.",
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
        "net_win_rate": net_win_rate,
        "profit_factor": net_profit_factor,
        "net_profit_factor": net_profit_factor,
        "total_gross_pnl": total_gross_pnl,
        "total_friction": total_friction,
        "total_pnl_rs": total_net_pnl,
        "total_net_pnl": total_net_pnl,
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
