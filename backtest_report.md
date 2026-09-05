# Backtest Report

**Symbols tested:** RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK  
**Period:** 60d  |  **Interval:** 15m  
**Strategies:** 21 (with 2-family confluence gate, min R:R 1.8)  
**ATR Trailing SL:** enabled (1.5 × ATR)  

---

## Summary

| Metric | Value |
|--------|-------|
| Total Trades | **496** |
| Win Rate | **44.2%** |
| Profit Factor | **1.53** |
| Total P&L | **₹4,826** (on ₹10,000/trade) |
| Expectancy (per trade) | ₹10 |
| Avg Win | +0.69% |
| Avg Loss | -0.35% |
| Avg R:R Achieved | 0.87 |
| Median R:R Achieved | 0.69 |
| Max Drawdown | ₹434 |
| Sharpe Ratio | 0.15 |
| Avg Bars Held | 7.6 |
| Trailing SL Exits | 328 (66% of trades) |

---

## Exit Breakdown

| Exit Reason | Count | % |
|-------------|-------|---|
| TRAILING_SL | 328 | 66% |
| SL | 107 | 22% |
| TARGET | 59 | 12% |
| EOD | 2 | 0% |

---

## Best & Worst Trades

**Best:** HDFCBANK SELL  Entry ₹782.1 → Exit ₹753.63  P&L **+3.64%**  Exit: TRAILING_SL

**Worst:** HDFCBANK BUY  Entry ₹806.05 → Exit ₹794.96  P&L **-1.38%**  Exit: SL

---

## Per-Symbol Breakdown

| Symbol | Trades | Win Rate | P&L (₹) |
|--------|--------|----------|---------|
| TCS | 100 | 46% | ₹2,185 |
| INFY | 101 | 44% | ₹1,028 |
| HDFCBANK | 95 | 44% | ₹748 |
| RELIANCE | 100 | 43% | ₹583 |
| ICICIBANK | 100 | 44% | ₹282 |

---

## Signal Family Contribution

| Family | Trades Involved | P&L (₹) |
|--------|-----------------|---------|
| oscillator | 265 | ₹3,890 |
| breakout | 290 | ₹3,215 |
| structure | 143 | ₹2,696 |
| trend | 238 | ₹2,640 |
| momentum | 206 | ₹2,222 |
| intraday | 19 | ₹-37 |
| volume | 84 | ₹-128 |

---

## Strategy Contribution

| Strategy | Wins | Losses | P&L (₹) |
|----------|------|--------|---------|
| Keltner Channel Breakout | 100 | 115 | ₹3,265 |
| Stochastic RSI | 58 | 53 | ₹2,218 |
| Williams %R | 47 | 44 | ₹2,124 |
| Volume Delta Divergence | 40 | 44 | ₹2,029 |
| Donchian Breakout | 79 | 97 | ₹1,905 |
| ADX Momentum | 28 | 25 | ₹1,734 |
| CCI Reversal | 48 | 46 | ₹1,628 |
| Parabolic SAR Trend | 92 | 121 | ₹1,562 |
| Institutional Absorption | 19 | 15 | ₹1,354 |
| MACD Cross | 66 | 87 | ₹1,004 |
| Bollinger Breakout | 30 | 39 | ₹861 |
| TSI Crossover | 27 | 33 | ₹730 |
| Awesome Oscillator Zero Cross | 20 | 26 | ₹574 |
| RSI Mean Reversion | 6 | 6 | ₹448 |
| Supertrend | 6 | 6 | ₹446 |
| Order Block FVG | 15 | 26 | ₹221 |
| EMA Crossover | 2 | 5 | ₹207 |
| MFI Exhaustion | 10 | 14 | ₹158 |
| VWAP Bounce | 9 | 10 | ₹-37 |
| Stochastic Reversal | 6 | 5 | ₹-47 |
| CMF Institutional Flow | 28 | 56 | ₹-128 |

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