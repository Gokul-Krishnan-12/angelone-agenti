"""
Market Regime Filter & Volatility Classifier.

Quantitatively classifies market structure into:
- TRENDING_BULL: Strong directional uptrend (ADX >= 20, Close > 50 EMA, +DI > -DI, KER >= 0.35)
- TRENDING_BEAR: Strong directional downtrend (ADX >= 20, Close < 50 EMA, -DI > +DI, KER >= 0.35)
- CHOPPY_RANGE: Range-bound consolidation or low-volatility squeeze (ADX < 20 or KER < 0.35)
- VOLATILE_EXPANSION: Outsized candle expansion / volatility explosion

Provides trade gating to prevent false breakout whipsaws and fee churn during
choppy market consolidation regimes (the exact cause of Nov 2025 & July 2026 drawdowns).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
import pandas as pd
from ta.trend import ADXIndicator
from ta.volatility import AverageTrueRange


@dataclass
class MarketRegimeResult:
    regime: (
        str  # "TRENDING_BULL" | "TRENDING_BEAR" | "CHOPPY_RANGE" | "VOLATILE_EXPANSION"
    )
    adx: float
    plus_di: float
    minus_di: float
    ker: float  # Kaufman Efficiency Ratio (0.0 to 1.0)
    ema20: float
    ema50: float
    atr_pct: float
    bb_width_pct: float
    is_squeezed: bool
    summary: str


def calculate_ker(series: pd.Series, period: int = 20) -> float:
    """Calculate Kaufman Efficiency Ratio over lookback period N.

    Direction = |Close_t - Close_{t-N}|
    Volatility = Sum_{i=0}^{N-1} |Close_{t-i} - Close_{t-i-1}|
    KER = Direction / Volatility (clamped [0.0, 1.0])
    """
    clean = series.dropna()
    if len(clean) < period + 1:
        return 0.0

    window = clean.iloc[-(period + 1) :]
    direction = abs(float(window.iloc[-1]) - float(window.iloc[0]))
    volatility = float(window.diff().abs().iloc[1:].sum())

    if volatility <= 1e-12 or np.isnan(volatility) or np.isnan(direction):
        return 0.0

    ker = direction / volatility
    return float(np.clip(ker, 0.0, 1.0))


def classify_market_regime(
    df: pd.DataFrame,
    adx_period: int = 14,
    ker_period: int = 20,
    min_adx: float = 20.0,
    min_ker: float = 0.35,
) -> MarketRegimeResult:
    """Classify the current market regime from candle dataframe.

    Parameters
    ----------
    df         : Candle DataFrame with ['open', 'high', 'low', 'close', 'volume']
    adx_period : Lookback window for ADX & DMI (default: 14)
    ker_period : Lookback window for Kaufman Efficiency Ratio (default: 20)
    min_adx    : Threshold for trend strength (default: 20.0)
    min_ker    : Threshold for directional efficiency (default: 0.35)
    """
    if df is None or len(df) < max(adx_period + 5, 20):
        return MarketRegimeResult(
            regime="CHOPPY_RANGE",
            adx=0.0,
            plus_di=0.0,
            minus_di=0.0,
            ker=0.0,
            ema20=0.0,
            ema50=0.0,
            atr_pct=0.0,
            bb_width_pct=0.0,
            is_squeezed=True,
            summary="Insufficient candle history for regime classification",
        )

    closes = df["close"].astype(float)
    highs = df["high"].astype(float)
    lows = df["low"].astype(float)
    curr_close = float(closes.iloc[-1])

    # 1. ADX & Directional Movement
    try:
        adx_ind = ADXIndicator(high=highs, low=lows, close=closes, window=adx_period)
        adx_series = adx_ind.adx()
        pdi_series = adx_ind.adx_pos()
        mdi_series = adx_ind.adx_neg()

        adx = float(adx_series.iloc[-1]) if not pd.isna(adx_series.iloc[-1]) else 0.0
        plus_di = (
            float(pdi_series.iloc[-1]) if not pd.isna(pdi_series.iloc[-1]) else 0.0
        )
        minus_di = (
            float(mdi_series.iloc[-1]) if not pd.isna(mdi_series.iloc[-1]) else 0.0
        )
    except Exception:
        adx, plus_di, minus_di = 0.0, 0.0, 0.0

    # 2. Kaufman Efficiency Ratio
    ker = calculate_ker(closes, period=ker_period)

    # 3. Moving Averages (EMA 20 & EMA 50)
    ema20 = float(closes.ewm(span=20, adjust=False).mean().iloc[-1])
    ema50 = (
        float(closes.ewm(span=50, adjust=False).mean().iloc[-1])
        if len(closes) >= 50
        else ema20
    )

    # 4. Volatility & Bollinger Band Width
    try:
        atr_series = AverageTrueRange(
            high=highs, low=lows, close=closes, window=14
        ).average_true_range()
        atr = float(atr_series.iloc[-1]) if not pd.isna(atr_series.iloc[-1]) else 0.0
        atr_pct = (atr / curr_close * 100.0) if curr_close > 0 else 0.0
    except Exception:
        atr_pct = 0.0

    sma20 = float(closes.rolling(20).mean().iloc[-1])
    std20 = float(closes.rolling(20).std().iloc[-1])
    bb_width_pct = (
        ((4.0 * std20) / sma20 * 100.0) if sma20 > 0 and not np.isnan(std20) else 0.0
    )
    is_squeezed = bb_width_pct < 1.8  # Compressed volatility squeeze

    # ── Regime Classification Logic ─────────────────────────────────
    if adx < min_adx or ker < min_ker or is_squeezed:
        regime = "CHOPPY_RANGE"
        summary = (
            f"Choppy / Squeeze regime (ADX {adx:.1f} < {min_adx} or KER {ker:.2f} < {min_ker}). "
            "Breakout setups are inhibited."
        )
    elif (
        curr_close > ema50 and plus_di > minus_di and adx >= min_adx and ker >= min_ker
    ):
        regime = "TRENDING_BULL"
        summary = (
            f"Strong Bullish Trend (ADX {adx:.1f}, +DI > -DI, Price > 50 EMA, KER {ker:.2f}). "
            "Favors Long breakouts and momentum continuation."
        )
    elif (
        curr_close < ema50 and minus_di > plus_di and adx >= min_adx and ker >= min_ker
    ):
        regime = "TRENDING_BEAR"
        summary = (
            f"Strong Bearish Trend (ADX {adx:.1f}, -DI > +DI, Price < 50 EMA, KER {ker:.2f}). "
            "Favors Short breakdowns and trend continuation."
        )
    else:
        # Transitional / moderate regime
        regime = "CHOPPY_RANGE" if adx < 22 else "VOLATILE_EXPANSION"
        summary = f"Mixed regime (ADX {adx:.1f}, KER {ker:.2f}). Caution advised on aggressive entries."

    return MarketRegimeResult(
        regime=regime,
        adx=round(adx, 2),
        plus_di=round(plus_di, 2),
        minus_di=round(minus_di, 2),
        ker=round(ker, 3),
        ema20=round(ema20, 2),
        ema50=round(ema50, 2),
        atr_pct=round(atr_pct, 2),
        bb_width_pct=round(bb_width_pct, 2),
        is_squeezed=is_squeezed,
        summary=summary,
    )


def is_trade_allowed_by_regime(
    regime: MarketRegimeResult,
    direction: str,
    strategy_family: str,
    block_choppy_breakouts: bool = True,
    strict_trend_alignment: bool = True,
) -> Tuple[bool, str]:
    """Determine whether a candidate trade is mathematically permitted under the current market regime.

    Parameters
    ----------
    regime                 : Evaluated MarketRegimeResult
    direction              : "BUY" or "SELL"
    strategy_family        : "breakout" | "trend" | "structure" | "volume" | "oscillator"
    block_choppy_breakouts : If True, blocks breakout setups when regime is CHOPPY_RANGE
    strict_trend_alignment : If True, forbids counter-trend breakout/trend trades

    Returns
    -------
    Tuple[bool, str] : (is_allowed, reason)
    """
    direction = direction.upper()
    family = strategy_family.lower()

    # 1. Choppy Regime Protection: Inhibit false breakouts
    if regime.regime == "CHOPPY_RANGE":
        if block_choppy_breakouts and family in ("breakout", "trend"):
            return (
                False,
                f"Blocked by Market Regime: {family.capitalize()} strategies disabled during "
                f"CHOPPY_RANGE (ADX: {regime.adx:.1f}, KER: {regime.ker:.2f}) to prevent false breakout churn.",
            )

    # 2. Strong Bull Trend Protection: Inhibit counter-trend shorts
    if regime.regime == "TRENDING_BULL":
        if (
            strict_trend_alignment
            and direction == "SELL"
            and family in ("breakout", "trend")
        ):
            return (
                False,
                f"Blocked by Market Regime: Counter-trend SELL prohibited during TRENDING_BULL "
                f"(Price > 50 EMA, +DI: {regime.plus_di:.1f} > -DI: {regime.minus_di:.1f}).",
            )

    # 3. Strong Bear Trend Protection: Inhibit counter-trend longs
    if regime.regime == "TRENDING_BEAR":
        if (
            strict_trend_alignment
            and direction == "BUY"
            and family in ("breakout", "trend")
        ):
            return (
                False,
                f"Blocked by Market Regime: Counter-trend BUY prohibited during TRENDING_BEAR "
                f"(Price < 50 EMA, -DI: {regime.minus_di:.1f} > +DI: {regime.plus_di:.1f}).",
            )

    return True, f"Trade permitted under {regime.regime} regime."
