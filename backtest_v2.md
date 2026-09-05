# Backtest Report

**Symbols tested:** RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK, HINDUNILVR, ITC, SBIN, BHARTIARTL, KOTAKBANK, LT, AXISBANK, ASIANPAINT, MARUTI, TITAN, SUNPHARMA, BAJFINANCE, WIPRO, ULTRACEMCO, NESTLEIND  
**Period:** 6mo  |  **Interval:** 1d  
**Strategies:** 21 (with 2-family confluence gate, min R:R 1.8)  
**ATR Trailing SL:** enabled (1.5 × ATR)  

---

## Summary

| Metric | Value |
|--------|-------|
| Total Trades | **102** |
| Win Rate | **52.9%** |
| Profit Factor | **1.94** |
| Total P&L | **₹5,675** (on ₹10,000/trade) |
| Expectancy (per trade) | ₹56 |
| Avg Win | +2.32% |
| Avg Loss | -1.30% |
| Avg R:R Achieved | 1.91 |
| Median R:R Achieved | 1.00 |
| Max Drawdown | ₹1,041 |
| Sharpe Ratio | 0.24 |
| Avg Bars Held | 4.3 |
| Trailing SL Exits | 16 (16% of trades) |

---

## Exit Breakdown

| Exit Reason | Count | % |
|-------------|-------|---|
| SL | 48 | 47% |
| TARGET | 29 | 28% |
| TRAILING_SL | 16 | 16% |
| EOD | 9 | 9% |

---

## Best & Worst Trades

**Best:** TCS SELL  Entry ₹2250.56 → Exit ₹2082.33  P&L **+7.48%**  Exit: TARGET

**Worst:** BAJFINANCE BUY  Entry ₹1164.0 → Exit ₹1119.05  P&L **-3.86%**  Exit: TRAILING_SL

---

## Per-Symbol Breakdown

| Symbol | Trades | Win Rate | P&L (₹) |
|--------|--------|----------|---------|
| WIPRO | 7 | 71% | ₹1,465 |
| AXISBANK | 5 | 100% | ₹962 |
| SBIN | 6 | 83% | ₹780 |
| INFY | 4 | 75% | ₹779 |
| KOTAKBANK | 6 | 50% | ₹628 |
| HDFCBANK | 3 | 67% | ₹622 |
| LT | 5 | 60% | ₹541 |
| TITAN | 4 | 50% | ₹530 |
| ASIANPAINT | 6 | 67% | ₹408 |
| SUNPHARMA | 3 | 67% | ₹352 |
| HINDUNILVR | 4 | 50% | ₹340 |
| TCS | 6 | 50% | ₹335 |
| BHARTIARTL | 4 | 50% | ₹261 |
| NESTLEIND | 7 | 43% | ₹78 |
| ITC | 6 | 67% | ₹43 |
| ICICIBANK | 3 | 0% | ₹-98 |
| RELIANCE | 5 | 20% | ₹-388 |
| ULTRACEMCO | 5 | 40% | ₹-427 |
| MARUTI | 6 | 17% | ₹-553 |
| BAJFINANCE | 7 | 29% | ₹-981 |

---

## Signal Family Contribution

| Family | Trades Involved | P&L (₹) |
|--------|-----------------|---------|
| oscillator | 50 | ₹3,783 |
| structure | 29 | ₹2,307 |
| volume | 19 | ₹2,216 |
| momentum | 45 | ₹2,097 |
| breakout | 70 | ₹2,002 |
| trend | 26 | ₹862 |

---

## Strategy Contribution

| Strategy | Wins | Losses | P&L (₹) |
|----------|------|--------|---------|
| Volume Delta Divergence | 16 | 11 | ₹3,007 |
| CMF Institutional Flow | 10 | 9 | ₹2,216 |
| Keltner Channel Breakout | 21 | 23 | ₹2,119 |
| Williams %R | 9 | 7 | ₹2,079 |
| CCI Reversal | 9 | 8 | ₹1,603 |
| MACD Cross | 18 | 10 | ₹1,346 |
| Bollinger Breakout | 7 | 3 | ₹1,135 |
| Stochastic Reversal | 4 | 2 | ₹909 |
| TSI Crossover | 9 | 9 | ₹877 |
| Parabolic SAR Trend | 12 | 12 | ₹567 |
| Awesome Oscillator Zero Cross | 9 | 9 | ₹525 |
| Stochastic RSI | 8 | 7 | ₹514 |
| ADX Momentum | 2 | 0 | ₹251 |
| Donchian Breakout | 15 | 16 | ₹172 |
| RSI Mean Reversion | 1 | 0 | ₹131 |
| EMA Crossover | 1 | 0 | ₹99 |
| MFI Exhaustion | 1 | 1 | ₹-7 |
| Order Block FVG | 1 | 2 | ₹-113 |

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