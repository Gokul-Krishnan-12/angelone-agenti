# Backtest Report

**Symbols tested:** ATHERENERG, OFSS, LAURUSLABS, BHEL, COFORGE, VEDL, RADICO, PAYTM, SONACOMS, IDEA, PNBHOUSING, KALYANKJIL, ADANIGREEN, MOTILALOFS, BOSCHLTD, ADANIPOWER, SOLARINDS, DIXON, ADANIENT, ADANIENSOL  
**Period:** 6mo  |  **Interval:** 1h  
**Strategies:** 21 (with 2-family confluence gate, min R:R 1.8)  
**ATR Trailing SL:** enabled (1.5 × ATR)  

---

## Summary

| Metric | Value |
|--------|-------|
| Total Trades | **719** |
| Win Rate | **43.7%** |
| Profit Factor | **1.54** |
| Total P&L | **₹31,889** (on ₹10,000/trade) |
| Expectancy (per trade) | ₹44 |
| Avg Win | +2.55% |
| Avg Loss | -1.28% |
| Avg R:R Achieved | 1.48 |
| Median R:R Achieved | 1.00 |
| Max Drawdown | ₹3,184 |
| Sharpe Ratio | 0.16 |
| Avg Bars Held | 8.2 |
| Trailing SL Exits | 141 (20% of trades) |

---

## Exit Breakdown

| Exit Reason | Count | % |
|-------------|-------|---|
| SL | 367 | 51% |
| TARGET | 203 | 28% |
| TRAILING_SL | 141 | 20% |
| EOD | 8 | 1% |

---

## Best & Worst Trades

**Best:** KALYANKJIL BUY  Entry ₹438.7 → Exit ₹508.15  P&L **+15.83%**  Exit: TRAILING_SL

**Worst:** ATHERENERG BUY  Entry ₹1285.1 → Exit ₹1201.52  P&L **-6.50%**  Exit: SL

---

## Per-Symbol Breakdown

| Symbol | Trades | Win Rate | P&L (₹) |
|--------|--------|----------|---------|
| BOSCHLTD | 32 | 44% | ₹5,471 |
| PAYTM | 36 | 61% | ₹3,978 |
| OFSS | 36 | 53% | ₹3,412 |
| IDEA | 31 | 58% | ₹2,801 |
| SOLARINDS | 36 | 47% | ₹2,670 |
| ADANIENT | 31 | 48% | ₹2,110 |
| KALYANKJIL | 35 | 31% | ₹2,099 |
| BHEL | 39 | 51% | ₹1,965 |
| COFORGE | 39 | 41% | ₹1,713 |
| ATHERENERG | 37 | 49% | ₹1,712 |
| LAURUSLABS | 31 | 55% | ₹1,395 |
| VEDL | 34 | 41% | ₹927 |
| PNBHOUSING | 37 | 38% | ₹821 |
| RADICO | 33 | 45% | ₹789 |
| MOTILALOFS | 33 | 42% | ₹644 |
| ADANIGREEN | 41 | 44% | ₹633 |
| DIXON | 42 | 36% | ₹326 |
| SONACOMS | 35 | 34% | ₹82 |
| ADANIENSOL | 42 | 33% | ₹-412 |
| ADANIPOWER | 39 | 28% | ₹-1,248 |

---

## Signal Family Contribution

| Family | Trades Involved | P&L (₹) |
|--------|-----------------|---------|
| breakout | 618 | ₹28,463 |
| oscillator | 241 | ₹16,462 |
| momentum | 312 | ₹15,300 |
| trend | 246 | ₹14,780 |
| volume | 184 | ₹9,242 |
| structure | 154 | ₹3,894 |

---

## Strategy Contribution

| Strategy | Wins | Losses | P&L (₹) |
|----------|------|--------|---------|
| Keltner Channel Breakout | 159 | 215 | ₹21,306 |
| Donchian Breakout | 170 | 204 | ₹17,113 |
| Bollinger Breakout | 81 | 74 | ₹16,486 |
| MACD Cross | 81 | 112 | ₹9,674 |
| Parabolic SAR Trend | 99 | 123 | ₹9,381 |
| Stochastic RSI | 56 | 71 | ₹9,262 |
| CMF Institutional Flow | 85 | 99 | ₹9,242 |
| TSI Crossover | 66 | 75 | ₹7,920 |
| Awesome Oscillator Zero Cross | 51 | 58 | ₹6,101 |
| Order Block FVG | 35 | 34 | ₹5,125 |
| EMA Crossover | 14 | 9 | ₹4,812 |
| Supertrend | 12 | 8 | ₹1,618 |
| Stochastic Reversal | 4 | 5 | ₹-47 |
| Volume Delta Divergence | 34 | 44 | ₹-103 |
| MFI Exhaustion | 4 | 10 | ₹-151 |
| Institutional Absorption | 8 | 11 | ₹-194 |

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