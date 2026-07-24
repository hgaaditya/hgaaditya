"""Mean-reversion strategy.

Fades extremes: buys when price closes below the lower Bollinger band with an
oversold RSI, sells when it closes above the upper band with an overbought RSI.
Targets the band mid; stops just beyond the band. This is the strategy the regime
classifier selects in range-bound conditions, where trend-following gets chopped.
"""

from __future__ import annotations

import pandas as pd

from tradingbot.core.events import Direction, Signal
from tradingbot.core.indicators import atr, bollinger, rsi
from tradingbot.strategies.base import Strategy


class MeanReversionStrategy(Strategy):
    def __init__(
        self,
        bb_period: int = 20,
        bb_mult: float = 2.0,
        rsi_period: int = 14,
        rsi_low: float = 30.0,
        rsi_high: float = 70.0,
        atr_period: int = 14,
        atr_stop_mult: float = 1.0,
    ):
        self.bb_period = bb_period
        self.bb_mult = bb_mult
        self.rsi_period = rsi_period
        self.rsi_low = rsi_low
        self.rsi_high = rsi_high
        self.atr_period = atr_period
        self.atr_stop_mult = atr_stop_mult
        self.warmup = max(bb_period, rsi_period, atr_period) + 2

    def on_bar(self, symbol: str, history: pd.DataFrame) -> list[Signal]:
        if not self.ready(history):
            return []

        close = history["close"]
        lower, mid, upper = bollinger(close, self.bb_period, self.bb_mult)
        r = rsi(close, self.rsi_period)
        a = float(atr(history["high"], history["low"], close, self.atr_period).iloc[-1])

        price = float(close.iloc[-1])
        lo, md, up = float(lower.iloc[-1]), float(mid.iloc[-1]), float(upper.iloc[-1])
        rsi_now = float(r.iloc[-1])
        ts = history.index[-1]

        if a <= 0:
            return []

        if price < lo and rsi_now < self.rsi_low:
            return [Signal(symbol, ts, Direction.LONG, min((self.rsi_low - rsi_now) / 30, 1.0),
                           self.name, reason=f"px<LB, RSI={rsi_now:.0f}",
                           stop_loss=price - self.atr_stop_mult * a, target=md)]
        if price > up and rsi_now > self.rsi_high:
            return [Signal(symbol, ts, Direction.SHORT, min((rsi_now - self.rsi_high) / 30, 1.0),
                           self.name, reason=f"px>UB, RSI={rsi_now:.0f}",
                           stop_loss=price + self.atr_stop_mult * a, target=md)]
        return []
