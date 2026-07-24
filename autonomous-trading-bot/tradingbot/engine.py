"""TradingEngine — the single bar-processing loop shared by every mode.

Backtest, paper, and (later) live all feed `Bar`s into `on_bar`. The only things
that differ between modes are the data feed and the broker adapter; the decision
logic — regime -> strategy -> signal -> risk -> order -> fill -> journal, plus
stop/target and square-off management — lives here and only here. That is the
core guarantee that a backtest reflects what live would have done.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd

from tradingbot.audit.journal import TradeJournal
from tradingbot.brokers.paper import PaperBroker
from tradingbot.config import AppConfig
from tradingbot.core.clock import MarketCalendar
from tradingbot.core.events import (
    Bar,
    Direction,
    Fill,
    Order,
    OrderType,
    Regime,
    Side,
    Signal,
)
from tradingbot.regime.classifier import RegimeClassifier
from tradingbot.risk.engine import RiskEngine
from tradingbot.strategies import build_strategy


@dataclass
class Trade:
    symbol: str
    direction: str
    qty: int
    entry_ts: datetime
    exit_ts: datetime
    entry_price: float
    exit_price: float
    pnl: float
    strategy: str
    exit_reason: str


class TradingEngine:
    def __init__(
        self,
        config: AppConfig,
        broker: PaperBroker,
        risk: RiskEngine,
        journal: TradeJournal,
        *,
        sentiment_bias: float = 0.0,
        logger=None,
    ):
        self.cfg = config
        self.broker = broker
        self.risk = risk
        self.journal = journal
        self.calendar = MarketCalendar()
        self.regime_clf = RegimeClassifier()
        self.sentiment_bias = sentiment_bias  # -1..1, tilts entry gating
        self.log = logger

        self.strategies = {
            sc.name: build_strategy(sc.name, sc.params)
            for sc in config.strategies
            if sc.enabled
        }
        # Bounded rolling window per symbol: indicators only need recent bars, so
        # keeping the full day would make per-bar cost grow O(n) for no benefit.
        self._lookback = 250
        self._history: dict[str, list[Bar]] = {}
        self._marks: dict[str, float] = {}
        self._open: dict[str, dict] = {}  # symbol -> {entry_fill, stop, target, ...}
        self.trades: list[Trade] = []
        self._day: date | None = None
        self._halt_logged = False

    # ---- public entry point ---------------------------------------------
    def on_bar(self, bar: Bar) -> None:
        self._roll_day(bar)
        hist = self._history.setdefault(bar.symbol, [])
        hist.append(bar)
        if len(hist) > self._lookback:
            del hist[0]
        self._marks[bar.symbol] = bar.close

        # Mark-to-market and update the daily kill-switch.
        equity = self.broker.equity(self._marks)
        self.journal.record_equity(bar.ts, equity)
        halted = self.risk.update_equity(equity)

        # Square-off or halt: flatten everything, take no new entries.
        if halted or self.calendar.is_square_off(bar.ts):
            if halted and not self._halt_logged:
                self.journal.record_halt(bar.ts, self.risk.halt_reason)
                self._log("halt", reason=self.risk.halt_reason)
                self._halt_logged = True
            self._flatten(bar, reason="square_off" if not halted else "kill_switch")
            return

        # Manage exits on the current position for this symbol first.
        self._manage_exit(bar)

        # Then look for a new entry if flat in this symbol.
        if bar.symbol not in self._open:
            self._seek_entry(bar)

    # ---- lifecycle -------------------------------------------------------
    def _roll_day(self, bar: Bar) -> None:
        day = bar.ts.date()
        if self._day != day:
            self._day = day
            self.risk.start_day(self.broker.equity(self._marks) if self._marks else self.cfg.risk.starting_capital)
            self._halt_logged = False

    def _history_df(self, symbol: str) -> pd.DataFrame:
        bars = self._history[symbol]
        return pd.DataFrame(
            {
                "open": [b.open for b in bars],
                "high": [b.high for b in bars],
                "low": [b.low for b in bars],
                "close": [b.close for b in bars],
                "volume": [b.volume for b in bars],
            },
            index=pd.DatetimeIndex([b.ts for b in bars]),
        )

    # ---- entries ---------------------------------------------------------
    def _seek_entry(self, bar: Bar) -> None:
        hist = self._history_df(bar.symbol)
        regime = self.regime_clf.classify(hist)
        strat_name = self.regime_clf.strategy_for(regime)
        if strat_name is None or strat_name not in self.strategies:
            return

        for sig in self.strategies[strat_name].on_bar(bar.symbol, hist):
            self.journal.record_signal(sig)
            if sig.direction is Direction.FLAT:
                continue
            if not self._sentiment_allows(sig, regime):
                self._log("blocked_by_sentiment", symbol=sig.symbol, dir=sig.direction.value)
                continue
            self._try_enter(bar, sig)

    def _sentiment_allows(self, sig: Signal, regime: Regime) -> bool:  # noqa: ARG002
        tilt = self.sentiment_bias * self.cfg.sentiment.weight
        if tilt <= -0.15 and sig.direction is Direction.LONG:
            return False
        if tilt >= 0.15 and sig.direction is Direction.SHORT:
            return False
        return True

    def _try_enter(self, bar: Bar, sig: Signal) -> None:
        equity = self.broker.equity(self._marks)
        gross = sum(abs(p.qty) * self._marks.get(s, 0.0) for s, p in self.broker.positions().items())
        decision = self.risk.check(sig, bar.close, equity, len(self.broker.positions()), gross)
        self.journal.record_risk(sig.symbol, bar.ts, decision)
        if not decision.approved or decision.qty <= 0:
            return

        side = Side.BUY if sig.direction is Direction.LONG else Side.SELL
        order = Order(sig.symbol, side, decision.qty, OrderType.MARKET, bar.ts,
                      tag=f"{sig.strategy}:entry")
        self.journal.record_order(order)
        fill = self.broker.place_order(order, bar.close)
        self.journal.record_fill(fill)
        self._open[sig.symbol] = {
            "entry_fill": fill,
            "direction": sig.direction,
            "stop": decision.stop_loss,
            "target": sig.target,
            "strategy": sig.strategy,
        }
        self._log("entry", symbol=sig.symbol, dir=sig.direction.value, qty=decision.qty,
                  price=round(fill.price, 2), reason=sig.reason)

    # ---- exits -----------------------------------------------------------
    def _manage_exit(self, bar: Bar) -> None:
        state = self._open.get(bar.symbol)
        if not state:
            return
        stop, target = state["stop"], state["target"]
        is_long = state["direction"] is Direction.LONG

        exit_price: float | None = None
        reason = ""
        if is_long:
            if stop is not None and bar.low <= stop:
                exit_price, reason = stop, "stop"
            elif target is not None and bar.high >= target:
                exit_price, reason = target, "target"
        else:
            if stop is not None and bar.high >= stop:
                exit_price, reason = stop, "stop"
            elif target is not None and bar.low <= target:
                exit_price, reason = target, "target"

        if exit_price is not None:
            self._close(bar, exit_price, reason)

    def _close(self, bar: Bar, price: float, reason: str) -> None:
        state = self._open.pop(bar.symbol, None)
        if not state:
            return
        entry: Fill = state["entry_fill"]
        qty = entry.qty
        is_long = state["direction"] is Direction.LONG
        side = Side.SELL if is_long else Side.BUY

        order = Order(bar.symbol, side, qty, OrderType.MARKET, bar.ts,
                      tag=f"{state['strategy']}:exit:{reason}")
        self.journal.record_order(order)
        fill = self.broker.place_order(order, price)
        self.journal.record_fill(fill)

        gross_pnl = (fill.price - entry.price) * qty * (1 if is_long else -1)
        pnl = gross_pnl - entry.taxes - fill.taxes
        self.trades.append(Trade(
            symbol=bar.symbol, direction=state["direction"].value, qty=qty,
            entry_ts=entry.ts, exit_ts=bar.ts, entry_price=entry.price,
            exit_price=fill.price, pnl=pnl, strategy=state["strategy"], exit_reason=reason,
        ))
        self._log("exit", symbol=bar.symbol, reason=reason, price=round(fill.price, 2),
                  pnl=round(pnl, 2))

    def _flatten(self, bar: Bar, reason: str) -> None:
        if bar.symbol in self._open:
            self._close(bar, bar.close, reason)

    # ---- misc ------------------------------------------------------------
    def _log(self, event: str, **kw) -> None:
        if self.log is not None:
            self.log.info(event, **kw)
