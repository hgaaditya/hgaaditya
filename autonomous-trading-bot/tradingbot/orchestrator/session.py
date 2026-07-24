"""Session — assemble a fully wired run (broker + risk + journal + engine).

This is the composition root: it reads config, picks the broker (paper by
default; live adapters are gated), builds the sentiment provider, computes the
day's bias, and hands back a ready TradingEngine. Both the paper runner and the
scheduler build on it.
"""

from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

from tradingbot.audit.journal import TradeJournal
from tradingbot.brokers.paper import PaperBroker
from tradingbot.config import AppConfig
from tradingbot.engine import TradingEngine
from tradingbot.logging_setup import setup_logging
from tradingbot.risk.engine import RiskEngine
from tradingbot.sentiment import build_sentiment


class Session:
    def __init__(self, config: AppConfig, headlines: list[str] | None = None):
        self.cfg = config
        self.run_id = f"{config.mode}_" + uuid.uuid4().hex[:10]
        runs = Path(config.runs_dir)
        self.log = setup_logging(log_file=runs / self.run_id / "session.jsonl")
        self.journal = TradeJournal(runs / self.run_id / "journal.sqlite", self.run_id)

        # Broker selection. Only paper is enabled by default; live adapters are
        # deliberately gated behind explicit, compliant configuration.
        if config.mode == "live":  # pragma: no cover - guarded path
            raise RuntimeError(
                "Live mode is not enabled in this build. Complete broker algo "
                "registration + static-IP whitelisting first (docs/COMPLIANCE.md), "
                "then wire a real BrokerAdapter here."
            )
        self.broker = PaperBroker(config.risk.starting_capital, config.costs)
        self.risk = RiskEngine(config.risk)

        # Daily sentiment bias -> feeds entry gating in the engine.
        provider = build_sentiment(config.sentiment.provider)
        if headlines is not None and hasattr(provider, "headlines"):
            provider.headlines = headlines
        self.sentiment = provider.daily_bias(date.today(), config.market.symbols)

        self.engine = TradingEngine(
            config, self.broker, self.risk, self.journal,
            sentiment_bias=self.sentiment.score, logger=self.log,
        )

    def start(self) -> None:
        self.journal.start_run(self.cfg.mode, self.cfg.model_dump())
        self.log.info(
            "session_start", run_id=self.run_id, mode=self.cfg.mode,
            capital=self.cfg.risk.starting_capital, sentiment=self.sentiment.label,
        )

    def close(self) -> None:
        self.log.info("session_close", run_id=self.run_id,
                      equity=self.broker.equity(self.engine._marks),
                      chain_ok=self.journal.verify_chain())
        self.journal.close()
