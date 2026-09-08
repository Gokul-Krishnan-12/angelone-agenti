"""Tests for the NSE F&O Universe module and caching."""

from __future__ import annotations

from backend.fno_universe import FNO_UNIVERSE, get_fno_universe


def test_fno_universe_bundled_count():
    """Verify that the bundled F&O list contains >= 200 liquid derivative symbols."""
    assert len(FNO_UNIVERSE) >= 200
    # Common high-momentum and high-volume F&O names must be included
    assert "RELIANCE" in FNO_UNIVERSE
    assert "TCS" in FNO_UNIVERSE
    assert "MCX" in FNO_UNIVERSE
    assert "COFORGE" in FNO_UNIVERSE
    assert "DIXON" in FNO_UNIVERSE
    assert "POLYCAB" in FNO_UNIVERSE


def test_fno_universe_clean_symbols():
    """Verify no test symbols or indices exist in the F&O list."""
    for symbol in FNO_UNIVERSE:
        assert not symbol.endswith("TEST")
        assert not symbol.startswith("NIFTY")
        assert not symbol.startswith("BANKNIFTY")
        assert symbol.isupper()


def test_get_fno_universe_returns_copy(monkeypatch):
    """Verify get_fno_universe returns a list and does not mutate cached object."""
    first = get_fno_universe()
    second = get_fno_universe()

    assert isinstance(first, list)
    assert len(first) >= 200
    assert first == second
    assert first is not second
