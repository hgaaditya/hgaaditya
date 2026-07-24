"""Regime classifier — the "which algorithm to apply" decision.

This is deliberately a transparent, rule-based classifier (ADX for trend
strength, Bollinger-band width for volatility) rather than an opaque model. It is
interpretable, has no training/overfitting risk, and is the natural baseline the
Phase-3 self-learning loop will be measured against before anything replaces it.

Mapping:
    strong ADX + rising    -> TREND_UP   -> trend strategy (long bias)
    strong ADX + falling   -> TREND_DOWN -> trend strategy (short bias)
    wide bands / high vol   -> HIGH_VOL   -> stand aside (protect capital)
    otherwise               -> RANGE      -> mean-reversion strategy
"""

from __future__ import annotations

import pandas as pd

from tradingbot.core.events import Regime
from tradingbot.core.indicators import adx, bollinger, ema

# Which strategy handles each regime. HIGH_VOL maps to None = do not trade.
REGIME_STRATEGY: dict[Regime, str | None] = {
    Regime.TREND_UP: "trend",
    Regime.TREND_DOWN: "trend",
    Regime.RANGE: "mean_reversion",
    Regime.HIGH_VOL: None,
    Regime.UNKNOWN: None,
}


class RegimeClassifier:
    def __init__(
        self,
        adx_trend: float = 22.0,
        vol_high: float = 0.02,   # BB width / price above this = high vol
        warmup: int = 30,
    ):
        self.adx_trend = adx_trend
        self.vol_high = vol_high
        self.warmup = warmup

    def classify(self, history: pd.DataFrame) -> Regime:
        if len(history) < self.warmup:
            return Regime.UNKNOWN

        close = history["close"]
        adx_now = float(adx(history["high"], history["low"], close, 14).iloc[-1])
        lower, mid, upper = bollinger(close, 20, 2.0)
        width = float((upper.iloc[-1] - lower.iloc[-1]) / max(mid.iloc[-1], 1e-9))
        trend = ema(close, 9).iloc[-1] - ema(close, 21).iloc[-1]

        if width >= self.vol_high:
            return Regime.HIGH_VOL
        if adx_now >= self.adx_trend:
            return Regime.TREND_UP if trend >= 0 else Regime.TREND_DOWN
        return Regime.RANGE

    def strategy_for(self, regime: Regime) -> str | None:
        return REGIME_STRATEGY.get(regime)
