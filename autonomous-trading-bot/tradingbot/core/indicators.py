"""Vectorized technical indicators (pandas/numpy only, no native deps).

Kept dependency-free on purpose so the core installs and tests anywhere. If you
later want the full TA-Lib/pandas-ta catalogue, add it under the `research`
extra — these functions match the standard definitions.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period, min_periods=period).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    # When avg_loss == 0 (no down moves) rs -> inf and RSI -> 100, which is the
    # correct "maximally overbought" reading. fillna(50) only covers the warmup.
    rs = avg_gain / avg_loss
    return (100 - 100 / (1 + rs)).fillna(50.0)


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    ranges = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    )
    return ranges.max(axis=1)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr = true_range(high, low, close)
    return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def bollinger(close: pd.Series, period: int = 20, mult: float = 2.0):
    mid = sma(close, period)
    std = close.rolling(period, min_periods=period).std(ddof=0)
    upper = mid + mult * std
    lower = mid - mult * std
    return lower, mid, upper


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average Directional Index — trend-strength measure (Wilder)."""
    up = high.diff()
    down = -low.diff()
    plus_dm = ((up > down) & (up > 0)) * up
    minus_dm = ((down > up) & (down > 0)) * down
    tr = true_range(high, low, close)
    atr_ = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr_
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr_
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    return dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean().fillna(0.0)
