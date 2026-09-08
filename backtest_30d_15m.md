# Backtest Report

**Symbols tested:** RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK  
**Period:** 30d  |  **Interval:** 15m  
**Strategies:** 21 (with 2-family confluence gate, min R:R 1.8)  
**ATR Trailing SL:** enabled (1.5 × ATR)  

---

## Summary

| Metric | Value |
|--------|-------|
| Total Trades | **250** |
| Win Rate | **43.2%** |
| Profit Factor | **1.39** |
| Total P&L | **₹1,697** (on ₹10,000/trade) |
| Expectancy (per trade) | ₹7 |
| Avg Win | +0.61% |
| Avg Loss | -0.33% |
| Avg R:R Achieved | 0.85 |
| Median R:R Achieved | 0.77 |
| Max Drawdown | ₹388 |
| Sharpe Ratio | 0.12 |
| Avg Bars Held | 6.8 |
| Trailing SL Exits | 163 (65% of trades) |

---

## Exit Breakdown

| Exit Reason | Count | % |
|-------------|-------|---|
| TRAILING_SL | 163 | 65% |
| SL | 60 | 24% |
| TARGET | 22 | 9% |
| EOD | 5 | 2% |

---

## Best & Worst Trades

**Best:** INFY SELL  Entry ₹1130.0 → Exit ₹1092.8  P&L **+3.29%**  Exit: EOD

**Worst:** INFY SELL  Entry ₹1121.8 → Exit ₹1134.28  P&L **-1.11%**  Exit: TRAILING_SL

---

## Per-Symbol Breakdown

| Symbol | Trades | Win Rate | P&L (₹) |
|--------|--------|----------|---------|
| TCS | 50 | 44% | ₹787 |
| HDFCBANK | 46 | 41% | ₹421 |
| RELIANCE | 50 | 50% | ₹320 |
| INFY | 50 | 40% | ₹310 |
| ICICIBANK | 54 | 41% | ₹-143 |

---

## Signal Family Contribution

| Family | Trades Involved | P&L (₹) |
|--------|-----------------|---------|
| trend | 115 | ₹1,630 |
| oscillator | 130 | ₹1,434 |
| structure | 64 | ₹1,025 |
| breakout | 142 | ₹562 |
| momentum | 111 | ₹346 |
| intraday | 10 | ₹12 |
| volume | 41 | ₹-544 |

---

## Strategy Contribution

| Strategy | Wins | Losses | P&L (₹) |
|----------|------|--------|---------|
| Keltner Channel Breakout | 47 | 55 | ₹982 |
| Stochastic RSI | 29 | 22 | ₹931 |
| Parabolic SAR Trend | 45 | 58 | ₹867 |
| CCI Reversal | 22 | 23 | ₹710 |
| ADX Momentum | 10 | 10 | ₹672 |
| Williams %R | 22 | 23 | ₹669 |
| Volume Delta Divergence | 17 | 22 | ₹516 |
| Institutional Absorption | 8 | 10 | ₹433 |
| RSI Mean Reversion | 3 | 4 | ₹272 |
| TSI Crossover | 16 | 19 | ₹199 |
| Awesome Oscillator Zero Cross | 10 | 13 | ₹103 |
| EMA Crossover | 1 | 1 | ₹42 |
| Supertrend | 1 | 3 | ₹22 |
| VWAP Bounce | 5 | 5 | ₹12 |
| Order Block FVG | 6 | 6 | ₹-5 |
| Stochastic Reversal | 3 | 3 | ₹-87 |
| Donchian Breakout | 31 | 48 | ₹-152 |
| MFI Exhaustion | 5 | 10 | ₹-157 |
| MACD Cross | 33 | 49 | ₹-166 |
| Bollinger Breakout | 6 | 18 | ₹-332 |
| CMF Institutional Flow | 8 | 33 | ₹-544 |

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