"""BacktestRunner — drive the shared TradingEngine over a historical feed.

Because it uses the same `TradingEngine` and `PaperBroker` as paper mode, a
backtest is not a separate reimplementation that can silently disagree with live
behaviour — it *is* the live behaviour, replayed over recorded bars.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path

from tradingbot.audit.journal import TradeJournal
from tradingbot.backtest.metrics import Metrics, compute_metrics
from tradingbot.brokers.paper import PaperBroker
from tradingbot.config import AppConfig
from tradingbot.data.feed import DataFeed
from tradingbot.engine import Trade, TradingEngine
from tradingbot.risk.engine import RiskEngine


@dataclass
class BacktestResult:
    run_id: str
    metrics: Metrics
    equity_curve: list[float]
    trades: list[Trade] = field(default_factory=list)
    chain_ok: bool = True


class BacktestRunner:
    def __init__(self, config: AppConfig, db_path: str | Path | None = None, logger=None):
        self.cfg = config
        self.run_id = "bt_" + uuid.uuid4().hex[:10]
        self.db_path = str(db_path or Path(config.runs_dir) / f"{self.run_id}.sqlite")
        self.logger = logger

    def run(self, feed: DataFeed, sentiment_bias: float = 0.0) -> BacktestResult:
        broker = PaperBroker(self.cfg.risk.starting_capital, self.cfg.costs)
        risk = RiskEngine(self.cfg.risk)
        journal = TradeJournal(self.db_path, self.run_id)
        journal.start_run("backtest", self.cfg.model_dump())

        engine = TradingEngine(
            self.cfg, broker, risk, journal, sentiment_bias=sentiment_bias, logger=self.logger
        )
        for bar in feed:
            engine.on_bar(bar)

        curve = [e for _, e in journal.equity_curve()]
        if not curve:
            curve = [self.cfg.risk.starting_capital]
        metrics = compute_metrics(curve, [t.pnl for t in engine.trades])
        chain_ok = journal.verify_chain()
        journal.close()

        return BacktestResult(
            run_id=self.run_id,
            metrics=metrics,
            equity_curve=curve,
            trades=engine.trades,
            chain_ok=chain_ok,
        )
