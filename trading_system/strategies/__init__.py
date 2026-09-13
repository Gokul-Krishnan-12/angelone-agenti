"""
Alpha strategy package for trading_system.
"""

from .base import BaseStrategy, ConfluenceGate, Signal
from .bollinger_expansion import BollingerExpansionStrategy
from .breakout_engine import BreakoutEngine
from .institutional_absorption import InstitutionalAbsorptionStrategy
from .institutional_fvg import InstitutionalFVGStrategy

__all__ = [
    "BaseStrategy",
    "Signal",
    "ConfluenceGate",
    "BreakoutEngine",
    "BollingerExpansionStrategy",
    "InstitutionalAbsorptionStrategy",
    "InstitutionalFVGStrategy",
]
