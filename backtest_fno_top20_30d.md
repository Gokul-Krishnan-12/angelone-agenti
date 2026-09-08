# Backtest Report

**Symbols tested:** ATHERENERG, PAYTM, MCX, MOTILALOFS, IDEA, DIVISLAB, SOLARINDS, KAYNES, APLAPOLLO, SAIL, ADANIENSOL, BOSCHLTD, GODREJCP, COFORGE, POLICYBZR, HINDZINC, COLPAL, JUBLFOOD, GLENMARK, GODREJPROP  
**Period:** 30d  |  **Interval:** 15m  
**Strategies:** 21 (with 2-family confluence gate, min R:R 1.8)  
**ATR Trailing SL:** enabled (1.5 × ATR)  

---

## Summary

| Metric | Value |
|--------|-------|
| Total Trades | **610** |
| Win Rate | **48.2%** |
| Profit Factor | **1.45** |
| Total P&L | **₹13,062** (on ₹10,000/trade) |
| Expectancy (per trade) | ₹21 |
| Avg Win | +1.32% |
| Avg Loss | -0.80% |
| Avg R:R Achieved | 1.45 |
| Median R:R Achieved | 1.00 |
| Max Drawdown | ₹1,955 |
| Sharpe Ratio | 0.15 |
| Avg Bars Held | 15.9 |
| Trailing SL Exits | 130 (21% of trades) |

---

## Exit Breakdown

| Exit Reason | Count | % |
|-------------|-------|---|
| SL | 324 | 53% |
| TARGET | 140 | 23% |
| TRAILING_SL | 130 | 21% |
| EOD | 16 | 3% |

---

## Best & Worst Trades

**Best:** PAYTM BUY  Entry ₹1421.8 → Exit ₹1559.98  P&L **+9.72%**  Exit: TARGET

**Worst:** IDEA BUY  Entry ₹14.72 → Exit ₹14.12  P&L **-4.05%**  Exit: SL

---

## Per-Symbol Breakdown

| Symbol | Trades | Win Rate | P&L (₹) |
|--------|--------|----------|---------|
| ADANIENSOL | 22 | 55% | ₹1,716 |
| ATHERENERG | 35 | 51% | ₹1,634 |
| BOSCHLTD | 38 | 37% | ₹1,110 |
| KAYNES | 33 | 64% | ₹1,097 |
| SAIL | 22 | 55% | ₹1,052 |
| JUBLFOOD | 32 | 50% | ₹1,025 |
| PAYTM | 33 | 45% | ₹881 |
| COLPAL | 28 | 64% | ₹804 |
| MCX | 32 | 59% | ₹669 |
| GODREJPROP | 28 | 46% | ₹596 |
| APLAPOLLO | 38 | 45% | ₹536 |
| HINDZINC | 37 | 41% | ₹434 |
| COFORGE | 27 | 44% | ₹367 |
| DIVISLAB | 31 | 48% | ₹365 |
| MOTILALOFS | 29 | 45% | ₹319 |
| POLICYBZR | 30 | 47% | ₹287 |
| GODREJCP | 24 | 50% | ₹226 |
| IDEA | 26 | 46% | ₹153 |
| GLENMARK | 26 | 42% | ₹22 |
| SOLARINDS | 39 | 38% | ₹-232 |

---

## Signal Family Contribution

| Family | Trades Involved | P&L (₹) |
|--------|-----------------|---------|
| breakout | 377 | ₹12,261 |
| structure | 226 | ₹10,060 |
| trend | 216 | ₹6,239 |
| momentum | 221 | ₹3,748 |
| oscillator | 306 | ₹2,713 |
| volume | 134 | ₹1,907 |
| intraday | 9 | ₹-172 |

---

## Strategy Contribution

| Strategy | Wins | Losses | P&L (₹) |
|----------|------|--------|---------|
| Donchian Breakout | 128 | 123 | ₹8,591 |
| Keltner Channel Breakout | 108 | 104 | ₹7,826 |
| Order Block FVG | 46 | 29 | ₹6,716 |
| Bollinger Breakout | 72 | 58 | ₹6,381 |
| Institutional Absorption | 31 | 28 | ₹5,656 |
| Parabolic SAR Trend | 86 | 71 | ₹5,098 |
| Volume Delta Divergence | 66 | 69 | ₹4,221 |
| TSI Crossover | 37 | 41 | ₹3,174 |
| Awesome Oscillator Zero Cross | 34 | 37 | ₹2,610 |
| EMA Crossover | 11 | 4 | ₹1,942 |
| CMF Institutional Flow | 57 | 77 | ₹1,907 |
| MACD Cross | 72 | 76 | ₹1,456 |
| Stochastic RSI | 47 | 62 | ₹1,416 |
| Stochastic Reversal | 11 | 8 | ₹1,342 |
| Supertrend | 8 | 5 | ₹530 |
| MFI Exhaustion | 18 | 19 | ₹509 |
| VWAP Bounce | 2 | 7 | ₹-172 |
| RSI Mean Reversion | 8 | 11 | ₹-233 |
| ADX Momentum | 32 | 39 | ₹-280 |
| CCI Reversal | 38 | 52 | ₹-1,816 |
| Williams %R | 51 | 60 | ₹-2,450 |

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