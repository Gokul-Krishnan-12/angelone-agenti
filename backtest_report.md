# Backtest Report

**Symbols tested:** ATHERENERG, PAYTM, MCX, MOTILALOFS, IDEA, DIVISLAB, SOLARINDS, APLAPOLLO, KAYNES, SAIL, ADANIENSOL, BOSCHLTD, GODREJCP, COFORGE, HINDZINC, COLPAL, POLICYBZR, GLENMARK, JUBLFOOD, GODREJPROP  
**Period:** 60d  |  **Interval:** 15m  
**Strategies:** 21 (with 2-family confluence gate, min R:R 1.8)  
**ATR Trailing SL:** enabled (1.5 × ATR)  

---

## Summary

| Metric | Value |
|--------|-------|
| Total Trades | **886** |
| Win Rate | **45.8%** |
| Profit Factor | **1.17** |
| Total P&L | **₹11,226** (on ₹10,000/trade) |
| Expectancy (per trade) | ₹13 |
| Avg Win | +1.65% |
| Avg Loss | -1.18% |
| Avg R:R Achieved | 1.40 |
| Median R:R Achieved | 1.00 |
| Max Drawdown | ₹3,467 |
| Sharpe Ratio | 0.07 |
| Avg Bars Held | 22.0 |
| Trailing SL Exits | 226 (26% of trades) |

---

## Exit Breakdown

| Exit Reason | Count | % |
|-------------|-------|---|
| SL | 475 | 54% |
| TRAILING_SL | 226 | 26% |
| TARGET | 167 | 19% |
| EOD | 18 | 2% |

---

## Best & Worst Trades

**Best:** PAYTM BUY  Entry ₹1421.8 → Exit ₹1559.98  P&L **+9.72%**  Exit: TARGET

**Worst:** ATHERENERG BUY  Entry ₹1296.0 → Exit ₹1233.45  P&L **-4.83%**  Exit: SL

---

## Per-Symbol Breakdown

| Symbol | Trades | Win Rate | P&L (₹) |
|--------|--------|----------|---------|
| BOSCHLTD | 42 | 45% | ₹2,941 |
| MCX | 46 | 61% | ₹2,471 |
| PAYTM | 47 | 49% | ₹2,384 |
| ATHERENERG | 45 | 51% | ₹1,887 |
| KAYNES | 55 | 51% | ₹1,646 |
| COFORGE | 49 | 49% | ₹1,050 |
| DIVISLAB | 35 | 63% | ₹1,026 |
| JUBLFOOD | 44 | 52% | ₹846 |
| SAIL | 58 | 47% | ₹747 |
| COLPAL | 40 | 48% | ₹324 |
| HINDZINC | 37 | 49% | ₹211 |
| POLICYBZR | 37 | 54% | ₹188 |
| GODREJCP | 40 | 50% | ₹95 |
| MOTILALOFS | 46 | 37% | ₹52 |
| APLAPOLLO | 34 | 41% | ₹-37 |
| IDEA | 43 | 42% | ₹-452 |
| ADANIENSOL | 42 | 21% | ₹-618 |
| GODREJPROP | 44 | 39% | ₹-684 |
| GLENMARK | 45 | 38% | ₹-1,353 |
| SOLARINDS | 57 | 35% | ₹-1,497 |

---

## Signal Family Contribution

| Family | Trades Involved | P&L (₹) |
|--------|-----------------|---------|
| breakout | 748 | ₹12,221 |
| trend | 304 | ₹9,033 |
| structure | 279 | ₹3,957 |
| oscillator | 303 | ₹3,338 |
| volume | 244 | ₹1,966 |
| momentum | 380 | ₹1,333 |

---

## Strategy Contribution

| Strategy | Wins | Losses | P&L (₹) |
|----------|------|--------|---------|
| Keltner Channel Breakout | 200 | 227 | ₹12,332 |
| Bollinger Breakout | 130 | 119 | ₹8,417 |
| Institutional Absorption | 42 | 28 | ₹8,301 |
| Parabolic SAR Trend | 122 | 138 | ₹6,058 |
| Stochastic RSI | 71 | 68 | ₹5,780 |
| Donchian Breakout | 233 | 279 | ₹3,445 |
| EMA Crossover | 26 | 13 | ₹2,878 |
| Supertrend | 21 | 16 | ₹2,766 |
| CMF Institutional Flow | 111 | 133 | ₹1,966 |
| Order Block FVG | 62 | 78 | ₹544 |
| TSI Crossover | 87 | 99 | ₹321 |
| MACD Cross | 105 | 123 | ₹89 |
| Stochastic Reversal | 2 | 3 | ₹-241 |
| Awesome Oscillator Zero Cross | 64 | 86 | ₹-1,032 |
| MFI Exhaustion | 7 | 14 | ₹-1,355 |
| Volume Delta Divergence | 53 | 64 | ₹-1,705 |

---

## Interpretation Notes

> [!NOTE]
> This backtest simulates entry at the **next bar's open** after a signal fires.
> Slippage, brokerage (₹20/order), STT, and exchange fees are **NOT deducted**.
> Add ~₹50–80 per round-trip to get realistic net P&L.
> 5-min VWAP strategies are less accurate on 1-day timeframe (VWAP resets daily).

> [!IMPORTANT]
> Past performance on historical data does not guarantee future results.
> Always paper-trade first before committing real capital.