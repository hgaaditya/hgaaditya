"""Daily orchestration: pre-market prep -> market loop -> post-market report.

In production (Phase 2) this maps onto APScheduler jobs anchored to the exchange
calendar (prep at ~09:00 IST, live loop 09:15-15:30, square-off 15:15, report
after close). For the foundation, `run_paper_session` replays a day of bars as if
live so the full pipeline runs end-to-end without a broker connection.
"""

from __future__ import annotations

import pandas as pd

from tradingbot.audit.reporter import print_metrics
from tradingbot.backtest.metrics import compute_metrics
from tradingbot.config import AppConfig
from tradingbot.data.feed import DataFrameFeed
from tradingbot.orchestrator.session import Session


def run_paper_session(
    config: AppConfig,
    df: pd.DataFrame,
    symbol: str,
    headlines: list[str] | None = None,
    show_report: bool = True,
):
    """Replay `df` (one or more sessions of OHLCV) through a paper Session."""
    session = Session(config, headlines=headlines)
    session.start()

    feed = DataFrameFeed(df, symbol=symbol, timeframe=config.market.timeframe)
    for bar in feed:
        session.engine.on_bar(bar)

    curve = [e for _, e in session.journal.equity_curve()] or [config.risk.starting_capital]
    metrics = compute_metrics(curve, [t.pnl for t in session.engine.trades])
    if show_report:
        print_metrics(metrics, title=f"Paper Session {session.run_id}")
    session.close()
    return session.run_id, metrics
