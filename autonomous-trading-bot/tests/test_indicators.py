import numpy as np
import pandas as pd

from tradingbot.core.indicators import adx, atr, bollinger, ema, rsi


def test_ema_tracks_constant_series():
    s = pd.Series([10.0] * 50)
    assert abs(ema(s, 9).iloc[-1] - 10.0) < 1e-9


def test_rsi_bounds_and_uptrend():
    up = pd.Series(np.linspace(100, 200, 100))
    r = rsi(up, 14)
    assert (r >= 0).all() and (r <= 100).all()
    assert r.iloc[-1] > 70  # strong uptrend -> overbought


def test_atr_positive():
    n = 60
    high = pd.Series(np.linspace(100, 110, n)) + 1
    low = pd.Series(np.linspace(100, 110, n)) - 1
    close = pd.Series(np.linspace(100, 110, n))
    a = atr(high, low, close, 14)
    assert a.iloc[-1] > 0


def test_bollinger_ordering():
    close = pd.Series(np.random.default_rng(1).normal(100, 2, 100))
    lower, mid, upper = bollinger(close, 20, 2.0)
    assert (upper.dropna() >= mid.dropna()).all()
    assert (mid.dropna() >= lower.dropna()).all()


def test_adx_range():
    n = 80
    high = pd.Series(np.linspace(100, 130, n)) + 1
    low = pd.Series(np.linspace(100, 130, n)) - 1
    close = pd.Series(np.linspace(100, 130, n))
    a = adx(high, low, close, 14)
    assert (a >= 0).all() and (a <= 100).all()
