"""
Tests for in-memory BarAggregator and real-time tick synthesis.
"""

from trading_system.core.bar_aggregator import BarAggregator, Candle


def test_bar_aggregator_intra_bar_updates():
    aggregator = BarAggregator(bar_interval_seconds=300)

    # Base timestamp at 10:00:00 (epoch 1700000100 -> bucket 1700000100 // 300 * 300 = 1700000100 // 300 = 5666667 * 300 = 1700000100)
    # Let's use 1700000000 (divisible by 300: 1700000000 % 300 == 200, bucket = 1699999800)
    base_ts = 1700000000.0

    # First tick: open=100.0
    aggregator.process_tick(
        token="2885",
        tradingsymbol="RELIANCE",
        ltp=100.0,
        day_volume=1000,
        tick_time=base_ts,
    )
    current = aggregator._current_bar["2885"]
    assert current.open == 100.0
    assert current.high == 100.0
    assert current.low == 100.0
    assert current.close == 100.0

    # Second tick in same bucket: ltp=105.0
    aggregator.process_tick(
        token="2885",
        tradingsymbol="RELIANCE",
        ltp=105.0,
        day_volume=1200,
        tick_time=base_ts + 30,
    )
    assert current.high == 105.0
    assert current.low == 100.0
    assert current.close == 105.0

    # Third tick in same bucket: ltp=98.0
    aggregator.process_tick(
        token="2885",
        tradingsymbol="RELIANCE",
        ltp=98.0,
        day_volume=1500,
        tick_time=base_ts + 60,
    )
    assert current.high == 105.0
    assert current.low == 98.0
    assert current.close == 98.0


def test_bar_aggregator_candle_closure_and_callback():
    closed_bars = []

    async def mock_callback(token, symbol, bar: Candle, df):
        closed_bars.append((token, symbol, bar, len(df)))

    aggregator = BarAggregator(bar_interval_seconds=300, on_candle_close=mock_callback)

    bucket_0 = 1700000100.0
    bucket_1 = bucket_0 + 350.0  # Crosses 300-second boundary

    # Bar 1 ticks
    aggregator.process_tick(
        token="2885", tradingsymbol="RELIANCE", ltp=100.0, tick_time=bucket_0
    )
    aggregator.process_tick(
        token="2885", tradingsymbol="RELIANCE", ltp=110.0, tick_time=bucket_0 + 50
    )

    # Bar 2 tick triggers closure of Bar 1
    aggregator.process_tick(
        token="2885", tradingsymbol="RELIANCE", ltp=108.0, tick_time=bucket_1
    )

    assert len(closed_bars) == 1
    token, symbol, bar, history_len = closed_bars[0]
    assert token == "2885"
    assert symbol == "RELIANCE"
    assert bar.open == 100.0
    assert bar.high == 110.0
    assert bar.close == 110.0
    assert bar.is_closed
    assert history_len == 1

    # Check history dataframe
    df = aggregator.get_history_df("2885")
    assert len(df) == 1
    assert df["high"].iloc[0] == 110.0
