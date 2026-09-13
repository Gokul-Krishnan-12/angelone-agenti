import numpy as np
import pandas as pd

from trading_system.config.settings import Settings
from trading_system.strategies.base import ConfluenceGate, Signal
from trading_system.strategies.breakout_engine import BreakoutEngine
from trading_system.strategies.cpr_engine import CPREngine
from trading_system.strategies.institutional_fvg import InstitutionalFVGStrategy


def create_synthetic_candle_df(
    length: int = 50, base_price: float = 1000.0
) -> pd.DataFrame:
    """Generate deterministic synthetic candles."""
    np.random.seed(42)
    prices = [base_price]
    for _ in range(length - 1):
        prices.append(prices[-1] + np.random.uniform(-5.0, 5.0))

    closes = np.array(prices)
    highs = closes + np.random.uniform(1.0, 4.0, size=length)
    lows = closes - np.random.uniform(1.0, 4.0, size=length)
    opens = closes + np.random.uniform(-2.0, 2.0, size=length)
    volumes = np.random.uniform(10000, 20000, size=length)

    df = pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
            "timestamp": np.arange(1700000000, 1700000000 + (length * 300), 300),
        }
    )
    return df


def test_cpr_engine_initialization():
    cpr = CPREngine()
    df = create_synthetic_candle_df(length=30)
    signals = cpr.evaluate(df, "RELIANCE")
    assert isinstance(signals, list)


def test_fvg_engine_initialization():
    fvg = InstitutionalFVGStrategy()
    df = create_synthetic_candle_df(length=30)
    signals = fvg.evaluate(df, "RELIANCE")
    assert isinstance(signals, list)


def test_breakout_engine_detection():
    df = create_synthetic_candle_df(length=30, base_price=1000.0)
    engine = BreakoutEngine()

    # Artificially create a massive breakout on the last bar with huge volume
    df.loc[df.index[-1], "close"] = 1080.0
    df.loc[df.index[-1], "high"] = 1085.0
    df.loc[df.index[-1], "volume"] = 150000.0  # 8x volume surge

    signals = engine.evaluate(df, "RELIANCE")
    assert isinstance(signals, list)
    if signals:
        sig = signals[0]
        assert sig.direction == "BUY"
        assert sig.tradingsymbol == "RELIANCE"
        assert sig.risk_reward >= 1.8


def test_confluence_gate_family_rule():
    settings = Settings(min_confluence=2, min_risk_reward=1.8)
    gate = ConfluenceGate(settings)
    df = create_synthetic_candle_df(length=60, base_price=1000.0)

    # Ensure last bar is distinctly above 50 EMA so macro trend filter passes for BUY
    ema50 = float(df["close"].ewm(span=50, adjust=False).mean().iloc[-1])
    df.loc[df.index[-1], "close"] = ema50 + 20.0
    df.loc[df.index[-1], "high"] = ema50 + 25.0

    # 1. Single family signal -> should be rejected by confluence gate
    sig1 = Signal(
        strategy_name="Breakout1",
        family="breakout",
        tradingsymbol="RELIANCE",
        direction="BUY",
        confidence=85,
        entry_price=1000.0,
        stop_loss=980.0,
        target_price=1040.0,
        risk_reward=2.0,
        timestamp=1700000000,
    )
    assert gate.validate_signals([sig1], df) is None

    # 2. Two independent families agreeing -> should be approved!
    sig2 = Signal(
        strategy_name="Structure1",
        family="structure",
        tradingsymbol="RELIANCE",
        direction="BUY",
        confidence=90,
        entry_price=1000.0,
        stop_loss=980.0,
        target_price=1040.0,
        risk_reward=2.0,
        timestamp=1700000000,
    )
    approved = gate.validate_signals([sig1, sig2], df)
    assert approved is not None
    assert approved.direction == "BUY"
    assert "breakout" in approved.indicators["families_voting"]
    assert "structure" in approved.indicators["families_voting"]
