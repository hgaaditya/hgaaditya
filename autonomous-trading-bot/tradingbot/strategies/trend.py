"""Trend / momentum strategy.

Goes long when a fast EMA crosses above a slow EMA with sufficient trend
strength (ADX), short on the opposite cross. Stops and targets are ATR-based so
risk scales with volatility. This is a baseline, not a money printer — its job is
to be the strategy the regime classifier selects in trending conditions.
"""

from __future__ import annotations

import pandas as pd

from tradingbot.core.events import Direction, Signal
from tradingbot.core.indicators import adx, atr, ema
from tradingbot.strategies.base import Strategy


class TrendStrategy(Strategy):
    def __init__(
        self,
        ema_fast: int = 9,
        ema_slow: int = 21,
        adx_min: float = 20.0,
        atr_period: int = 14,
        atr_stop_mult: float = 1.5,
        rr: float = 1.5,  # reward:risk multiple for the target
    ):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.adx_min = adx_min
        self.atr_period = atr_period
        self.atr_stop_mult = atr_stop_mult
        self.rr = rr
        self.warmup = max(ema_slow, atr_period, 14) + 2

    def on_bar(self, symbol: str, history: pd.DataFrame) -> list[Signal]:
        if not self.ready(history):
            return []

        close = history["close"]
        fast = ema(close, self.ema_fast)
        slow = ema(close, self.ema_slow)
        strength = adx(history["high"], history["low"], close, 14)
        atr_val = atr(history["high"], history["low"], close, self.atr_period)

        f_now, f_prev = fast.iloc[-1], fast.iloc[-2]
        s_now, s_prev = slow.iloc[-1], slow.iloc[-2]
        adx_now = float(strength.iloc[-1])
        a = float(atr_val.iloc[-1])
        price = float(close.iloc[-1])
        ts = history.index[-1]

        if adx_now < self.adx_min or a <= 0:
            return []

        crossed_up = f_prev <= s_prev and f_now > s_now
        crossed_down = f_prev >= s_prev and f_now < s_now

        if crossed_up:
            stop = price - self.atr_stop_mult * a
            return [Signal(symbol, ts, Direction.LONG, min(adx_now / 50, 1.0), self.name,
                           reason=f"EMA{self.ema_fast}>EMA{self.ema_slow}, ADX={adx_now:.0f}",
                           stop_loss=stop, target=price + self.rr * (price - stop))]
        if crossed_down:
            stop = price + self.atr_stop_mult * a
            return [Signal(symbol, ts, Direction.SHORT, min(adx_now / 50, 1.0), self.name,
                           reason=f"EMA{self.ema_fast}<EMA{self.ema_slow}, ADX={adx_now:.0f}",
                           stop_loss=stop, target=price - self.rr * (stop - price))]
        return []
