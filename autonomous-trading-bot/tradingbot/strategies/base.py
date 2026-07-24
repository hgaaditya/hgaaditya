"""Strategy interface.

A strategy is a pure function of recent history: it receives the rolling OHLCV
window for one symbol (current bar last) and returns zero or more Signals. It
holds no cash, places no orders, and knows nothing about risk — that separation
is what lets the same strategy run identically in backtest, paper, and live.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from tradingbot.core.events import Signal


class Strategy(ABC):
    #: minimum bars required before the strategy should emit signals
    warmup: int = 30

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def ready(self, history: pd.DataFrame) -> bool:
        return len(history) >= self.warmup

    @abstractmethod
    def on_bar(self, symbol: str, history: pd.DataFrame) -> list[Signal]:
        """Return signals given history (columns: open, high, low, close, volume;
        DatetimeIndex; last row is the current, just-closed bar)."""
