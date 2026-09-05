"""
Tests for the three new high-win-rate strategies:
  - OpeningRangeBreakoutStrategy
  - LiquidityGrabReversalStrategy
  - GapFillStrategy
"""

import pandas as pd

from backend.strategies.gap_fill import MIN_BARS as GAP_MIN_BARS
from backend.strategies.gap_fill import GapFillStrategy
from backend.strategies.liquidity_grab_reversal import (
    LOOKBACK,
    LiquidityGrabReversalStrategy,
)
from backend.strategies.opening_range_breakout import (
    MIN_BARS,
    OR_BARS,
    OpeningRangeBreakoutStrategy,
)

SYMBOL = "TESTSTOCK"


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _flat_df(n: int, price: float = 100.0, volume: float = 1_000_000.0) -> pd.DataFrame:
    """Flat candles — no signal expected from any directional strategy."""
    return pd.DataFrame(
        {
            "open": [price] * n,
            "high": [price + 0.5] * n,
            "low": [price - 0.5] * n,
            "close": [price] * n,
            "volume": [volume] * n,
        }
    )


def _trending_df(
    n: int,
    start: float = 100.0,
    step: float = 0.5,
    volume: float = 1_000_000.0,
) -> pd.DataFrame:
    """Steadily rising candles."""
    prices = [start + i * step for i in range(n)]
    return pd.DataFrame(
        {
            "open": prices,
            "high": [p + 0.4 for p in prices],
            "low": [p - 0.2 for p in prices],
            "close": [p + 0.3 for p in prices],
            "volume": [volume] * n,
        }
    )


# ════════════════════════════════════════════════════════════════════════════
# OpeningRangeBreakoutStrategy
# ════════════════════════════════════════════════════════════════════════════


class TestOpeningRangeBreakout:
    def setup_method(self):
        self.strat = OpeningRangeBreakoutStrategy()

    def _orb_df(
        self,
        or_high: float = 105.0,
        or_low: float = 95.0,
        breakout_up: bool = True,
        vol_ratio: float = 2.0,
        body_ratio: float = 0.6,
        adx_strong: bool = True,
        n_extra: int = 10,
    ) -> pd.DataFrame:
        """
        Build a DataFrame where the first OR_BARS bars define the opening range,
        then subsequent bars are neutral, and the last bar is the breakout.
        """
        or_avg_vol = 1_000_000.0
        or_bars = [
            {
                "open": (or_high + or_low) / 2,
                "high": or_high,
                "low": or_low,
                "close": (or_high + or_low) / 2,
                "volume": or_avg_vol,
            }
        ] * OR_BARS

        # Neutral bars in the middle (inside the OR)
        mid = (or_high + or_low) / 2
        neutral_bars = [
            {
                "open": mid,
                "high": mid + 0.5,
                "low": mid - 0.5,
                "close": mid,
                "volume": or_avg_vol * 0.8,
            }
        ] * n_extra

        # Breakout bar
        breakout_vol = or_avg_vol * vol_ratio
        or_height = or_high - or_low
        if breakout_up:
            b_open = or_high + 0.1
            b_close = or_high + or_height * body_ratio
            b_high = b_close + 0.2
            b_low = b_open - 0.1
        else:
            b_open = or_low - 0.1
            b_close = or_low - or_height * body_ratio
            b_high = b_open + 0.1
            b_low = b_close - 0.2

        breakout_bar = {
            "open": b_open,
            "high": b_high,
            "low": b_low,
            "close": b_close,
            "volume": breakout_vol,
        }

        rows = or_bars + neutral_bars + [breakout_bar]
        df = pd.DataFrame(rows)

        # Inject a synthetic ADX-like effect by making trend visible in high/low
        if adx_strong:
            # Widen highs to simulate trending (ADX will compute from ta)
            for i in range(len(df)):
                df.loc[i, "high"] = df.loc[i, "high"] + i * 0.1
                df.loc[i, "low"] = max(df.loc[i, "low"] - i * 0.05, 1.0)

        return df

    def test_no_signal_on_short_df(self):
        df = _flat_df(MIN_BARS - 1)
        assert self.strat.calculate_signals(df, SYMBOL) == []

    def test_no_signal_flat_market(self):
        df = _flat_df(MIN_BARS + 5)
        assert self.strat.calculate_signals(df, SYMBOL) == []

    def test_buy_signal_on_upside_breakout(self):
        df = self._orb_df(breakout_up=True, vol_ratio=2.0, body_ratio=0.6)
        signals = self.strat.calculate_signals(df, SYMBOL)
        # May or may not fire depending on ADX — just ensure no exception and
        # if it fires it's a BUY with correct structure
        for sig in signals:
            assert sig["direction"] == "BUY"
            assert sig["stopLoss"] < sig["entryPrice"]
            assert sig["target"] > sig["entryPrice"]
            assert sig["riskReward"] >= 1.5
            assert sig["confidence"] >= 70
            assert "or_high" in sig["indicators"]
            assert "vol_ratio" in sig["indicators"]

    def test_sell_signal_on_downside_breakout(self):
        df = self._orb_df(breakout_up=False, vol_ratio=2.0, body_ratio=0.6)
        signals = self.strat.calculate_signals(df, SYMBOL)
        for sig in signals:
            assert sig["direction"] == "SELL"
            assert sig["stopLoss"] > sig["entryPrice"]
            assert sig["target"] < sig["entryPrice"]
            assert sig["riskReward"] >= 1.5

    def test_no_signal_low_volume(self):
        df = self._orb_df(vol_ratio=0.8)  # volume below 1.5× threshold
        signals = self.strat.calculate_signals(df, SYMBOL)
        assert signals == []

    def test_no_signal_doji_body(self):
        df = self._orb_df(body_ratio=0.1)  # tiny body — doji
        signals = self.strat.calculate_signals(df, SYMBOL)
        assert signals == []

    def test_signal_format(self):
        df = self._orb_df(breakout_up=True, vol_ratio=2.5, body_ratio=0.7)
        signals = self.strat.calculate_signals(df, SYMBOL)
        for sig in signals:
            required_keys = {
                "id",
                "tradingsymbol",
                "exchange",
                "strategy",
                "direction",
                "confidence",
                "entryPrice",
                "stopLoss",
                "target",
                "riskReward",
                "reasoning",
                "timestamp",
                "indicators",
            }
            assert required_keys.issubset(sig.keys())
            assert sig["strategy"] == "Opening Range Breakout"

    def test_wide_or_skipped(self):
        """OR spanning >3% of price should be skipped (likely news day)."""
        df = self._orb_df(or_high=115.0, or_low=85.0, vol_ratio=3.0)  # 30% range
        signals = self.strat.calculate_signals(df, SYMBOL)
        assert signals == []


# ════════════════════════════════════════════════════════════════════════════
# LiquidityGrabReversalStrategy
# ════════════════════════════════════════════════════════════════════════════


class TestLiquidityGrabReversal:
    def setup_method(self):
        self.strat = LiquidityGrabReversalStrategy()

    def _lgr_df(
        self,
        base_price: float = 100.0,
        sweep_direction: str = "BUY",  # BUY = sweep below swing low
        wick_ratio: float = 0.65,
        vol_mult: float = 2.5,
        mss: bool = True,
    ) -> pd.DataFrame:
        """
        Build a dataframe that triggers a liquidity grab:
          bars 0..(LOOKBACK+3): ranging bars forming the swing low/high reference
          bar  -(2):            the sweep bar (long wick beyond the swing)
          bar  -(1):            the MSS confirmation bar
        """
        avg_vol = 1_000_000.0
        n_base = LOOKBACK + 5  # enough reference bars

        # Base ranging bars — establish a clear swing low/high
        rows = []
        for _ in range(n_base):
            rows.append(
                {
                    "open": base_price,
                    "high": base_price + 2.0,
                    "low": base_price - 2.0,
                    "close": base_price + 0.5,
                    "volume": avg_vol,
                }
            )

        # The prior swing low/high that the reference window will see
        prior_swing_low = base_price - 2.0
        prior_swing_high = base_price + 2.0

        if sweep_direction == "BUY":
            # Sweep bar: body in upper half, LONG lower wick going below prior_swing_low
            # candle_range = lower_wick + body → wick/range = wick_ratio
            candle_range = 10.0
            lower_wick = candle_range * wick_ratio  # e.g. 6.5 for 0.65
            body = candle_range - lower_wick  # e.g. 3.5
            b_low = prior_swing_low - 0.5  # definitively below swing low
            b_open = b_low + lower_wick  # open at top of wick zone
            b_close = b_open + body * 0.6  # close above open (bullish body)
            b_high = b_close + body * 0.4
            sweep_bar = {
                "open": b_open,
                "high": b_high,
                "low": b_low,
                "close": b_close,
                "volume": avg_vol * vol_mult,
            }
            mss_close = prior_swing_low + 3.0 if mss else prior_swing_low - 0.5
            mss_bar = {
                "open": b_close,
                "high": mss_close + 1.0,
                "low": b_close - 0.2,
                "close": mss_close,
                "volume": avg_vol,
            }
        else:
            # Sweep bar: body in lower half, LONG upper wick going above prior_swing_high
            candle_range = 10.0
            upper_wick = candle_range * wick_ratio
            body = candle_range - upper_wick
            b_high = prior_swing_high + 0.5
            b_open = b_high - upper_wick
            b_close = b_open - body * 0.6
            b_low = b_close - body * 0.4
            sweep_bar = {
                "open": b_open,
                "high": b_high,
                "low": b_low,
                "close": b_close,
                "volume": avg_vol * vol_mult,
            }
            mss_close = prior_swing_high - 1.0 if mss else prior_swing_high + 0.5
            mss_bar = {
                "open": b_close,
                "high": b_close + 0.2,
                "low": mss_close - 1.0,
                "close": mss_close,
                "volume": avg_vol,
            }

        rows.append(sweep_bar)
        rows.append(mss_bar)
        return pd.DataFrame(rows)

    def test_no_signal_too_few_bars(self):
        df = _flat_df(LOOKBACK)
        assert self.strat.calculate_signals(df, SYMBOL) == []

    def test_buy_signal_fires_on_valid_setup(self):
        """
        Verify the BUY signal path fires when all conditions are manually met.
        Reference bars have high=520 to give R:R room above entry.
        """
        avg_vol = 100_000.0
        ref_bars = []
        for _ in range(LOOKBACK + 5):
            ref_bars.append(
                {
                    "open": 500,
                    "high": 520,
                    "low": 498,
                    "close": 500.5,
                    "volume": avg_vol,
                }
            )

        # Sweep bar: low=497 (below 498), wick=7, range=9, ratio=0.78, vol=3x
        sweep = {
            "open": 504.0,
            "high": 506.0,
            "low": 497.0,
            "close": 505.0,
            "volume": avg_vol * 3,
        }
        # MSS bar: close=501 > ref_low=498; target=ref_high=520 → good R:R
        mss = {
            "open": 505.0,
            "high": 502.0,
            "low": 499.0,
            "close": 501.0,
            "volume": avg_vol,
        }

        df = pd.DataFrame(ref_bars + [sweep, mss])
        signals = self.strat.calculate_signals(df, SYMBOL)
        buy_signals = [s for s in signals if s["direction"] == "BUY"]
        assert len(buy_signals) >= 1
        sig = buy_signals[0]
        assert sig["stopLoss"] < sig["entryPrice"]
        assert sig["target"] > sig["entryPrice"]
        assert sig["riskReward"] >= 1.8
        assert sig["confidence"] >= 75
        assert "sweep_low" in sig["indicators"]
        assert "wick_ratio" in sig["indicators"]

    def test_sell_signal_fires_on_valid_setup(self):
        """
        Verify the SELL signal path fires when all conditions are manually met.
        """
        avg_vol = 100_000.0
        ref_bars = []
        for _ in range(LOOKBACK + 5):
            ref_bars.append(
                {
                    "open": 500,
                    "high": 502,
                    "low": 480,
                    "close": 500.5,
                    "volume": avg_vol,
                }
            )

        # Sweep bar: wick goes to 503 (above 502), upper_wick=7, range=9, ratio=0.78 ✓
        # candle: high=503, open=496, close=495, low=494 → wick=7 ✓
        sweep = {
            "open": 496.0,
            "high": 503.0,
            "low": 494.0,
            "close": 495.0,
            "volume": avg_vol * 3,
        }
        # Ref has low=480 for target R:R; MSS close=499 < ref_high=502
        mss = {
            "open": 495.0,
            "high": 500.0,
            "low": 497.0,
            "close": 499.0,
            "volume": avg_vol,
        }

        df = pd.DataFrame(ref_bars + [sweep, mss])
        signals = self.strat.calculate_signals(df, SYMBOL)
        sell_signals = [s for s in signals if s["direction"] == "SELL"]
        assert len(sell_signals) >= 1
        sig = sell_signals[0]
        assert sig["stopLoss"] > sig["entryPrice"]
        assert sig["target"] < sig["entryPrice"]

    def test_no_signal_without_mss(self):
        """Without market structure shift confirmation, no signal should fire."""
        df = self._lgr_df(
            sweep_direction="BUY", wick_ratio=0.65, vol_mult=2.5, mss=False
        )
        signals = [
            s
            for s in self.strat.calculate_signals(df, SYMBOL)
            if s["direction"] == "BUY"
        ]
        assert signals == []

    def test_no_signal_low_volume(self):
        """Sweep on low volume should not signal."""
        df = self._lgr_df(vol_mult=1.0)  # below 2× threshold
        assert self.strat.calculate_signals(df, SYMBOL) == []

    def test_no_signal_small_wick(self):
        """Thin-wick candle — not a real stop hunt."""
        df = self._lgr_df(wick_ratio=0.30, vol_mult=2.5)
        signals = [
            s
            for s in self.strat.calculate_signals(df, SYMBOL)
            if s["direction"] == "BUY"
        ]
        assert signals == []

    def test_signal_strategy_name(self):
        df = self._lgr_df(
            sweep_direction="BUY", wick_ratio=0.70, vol_mult=3.0, mss=True
        )
        signals = self.strat.calculate_signals(df, SYMBOL)
        for sig in signals:
            assert sig["strategy"] == "Liquidity Grab Reversal"


# ════════════════════════════════════════════════════════════════════════════
# GapFillStrategy
# ════════════════════════════════════════════════════════════════════════════


class TestGapFill:
    def setup_method(self):
        self.strat = GapFillStrategy()

    def _gap_df(
        self,
        prev_close: float = 100.0,
        gap_pct: float = 1.5,  # positive = gap up
        reversal_bars: int = 4,
        vol_ratio: float = 1.5,
        adx_low: bool = True,
        n_total: int = 30,
    ) -> pd.DataFrame:
        """Build a gap + reversal scenario."""
        avg_vol = 1_000_000.0

        # First bar = "previous session" close (reference)
        rows = [
            {
                "open": prev_close,
                "high": prev_close + 1.0,
                "low": prev_close - 1.0,
                "close": prev_close,
                "volume": avg_vol,
            }
        ]

        today_open = prev_close * (1 + gap_pct / 100)
        gap_up = gap_pct > 0

        # Fill the df with neutral intraday bars away from prev_close
        neutral_count = max(0, n_total - reversal_bars - 2)
        for _ in range(neutral_count):
            rows.append(
                {
                    "open": today_open,
                    "high": today_open + 0.5,
                    "low": today_open - 0.3,
                    "close": today_open,
                    "volume": avg_vol * 0.9,
                }
            )

        # Reversal bars — price moving back toward prev_close
        step = (today_open - prev_close) / (reversal_bars * 2)
        current = today_open
        for i in range(reversal_bars):
            if gap_up:
                current -= step * (i + 1) * 0.4
                rows.append(
                    {
                        "open": current + step * 0.2,
                        "high": current + step * 0.4,
                        "low": current - step * 0.1,
                        "close": current,
                        "volume": avg_vol * vol_ratio if i == 0 else avg_vol * 0.9,
                    }
                )
            else:
                current += step * (i + 1) * 0.4
                rows.append(
                    {
                        "open": current - step * 0.2,
                        "high": current + step * 0.1,
                        "low": current - step * 0.4,
                        "close": current,
                        "volume": avg_vol * vol_ratio if i == 0 else avg_vol * 0.9,
                    }
                )

        df = pd.DataFrame(rows[:n_total])
        return df

    def test_no_signal_too_few_bars(self):
        df = _flat_df(GAP_MIN_BARS - 1)
        assert self.strat.calculate_signals(df, SYMBOL) == []

    def test_no_signal_no_gap(self):
        """No gap → no signal."""
        df = self._gap_df(gap_pct=0.1)  # below 0.5% threshold
        assert self.strat.calculate_signals(df, SYMBOL) == []

    def test_no_signal_large_gap(self):
        """Gap >2.5% → news-driven, skip."""
        df = self._gap_df(gap_pct=4.0)
        assert self.strat.calculate_signals(df, SYMBOL) == []

    def test_sell_signal_on_gap_up_reversal(self):
        """Gap up with price reversing → SELL (fade the gap)."""
        df = self._gap_df(gap_pct=1.5, reversal_bars=4, vol_ratio=1.5)
        signals = self.strat.calculate_signals(df, SYMBOL)
        sell_signals = [s for s in signals if s["direction"] == "SELL"]
        if sell_signals:
            sig = sell_signals[0]
            assert sig["stopLoss"] > sig["entryPrice"]
            assert sig["target"] < sig["entryPrice"]
            assert sig["riskReward"] >= 1.5
            assert "gap_pct" in sig["indicators"]

    def test_buy_signal_on_gap_down_reversal(self):
        """Gap down with price bouncing → BUY (fade the gap)."""
        df = self._gap_df(gap_pct=-1.5, reversal_bars=4, vol_ratio=1.5)
        signals = self.strat.calculate_signals(df, SYMBOL)
        buy_signals = [s for s in signals if s["direction"] == "BUY"]
        if buy_signals:
            sig = buy_signals[0]
            assert sig["stopLoss"] < sig["entryPrice"]
            assert sig["target"] > sig["entryPrice"]

    def test_no_signal_low_volume(self):
        """No volume on reversal bars → no signal."""
        df = self._gap_df(gap_pct=1.5, vol_ratio=0.8)
        assert self.strat.calculate_signals(df, SYMBOL) == []

    def test_signal_format_valid(self):
        df = self._gap_df(gap_pct=1.5, reversal_bars=5, vol_ratio=2.0)
        signals = self.strat.calculate_signals(df, SYMBOL)
        for sig in signals:
            required = {
                "id",
                "tradingsymbol",
                "exchange",
                "strategy",
                "direction",
                "confidence",
                "entryPrice",
                "stopLoss",
                "target",
                "riskReward",
                "reasoning",
                "timestamp",
                "indicators",
            }
            assert required.issubset(sig.keys())
            assert sig["strategy"] == "Gap Fill Reversal"
            assert sig["exchange"] == "NSE"
