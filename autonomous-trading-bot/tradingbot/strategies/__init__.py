"""Trading strategies. Each maps recent price history to Signals; the regime
classifier decides which one is allowed to act at any given time."""

from __future__ import annotations

from tradingbot.strategies.base import Strategy
from tradingbot.strategies.mean_reversion import MeanReversionStrategy
from tradingbot.strategies.trend import TrendStrategy

_REGISTRY = {
    "trend": TrendStrategy,
    "mean_reversion": MeanReversionStrategy,
}


def build_strategy(name: str, params: dict | None = None) -> Strategy:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown strategy '{name}'. Known: {list(_REGISTRY)}")
    return _REGISTRY[name](**(params or {}))


__all__ = ["Strategy", "TrendStrategy", "MeanReversionStrategy", "build_strategy"]
