"""Walk-forward evaluation.

The right way to judge whether a strategy/parameter set generalizes: repeatedly
train/select on an in-sample window, then measure on the *next* out-of-sample
window it never saw. Aggregated out-of-sample performance is the only number
worth trusting, and it's what the Phase-3 self-learning loop will gate on to
avoid promoting curve-fit parameters.

This foundation implementation runs the engine over consecutive out-of-sample
folds and aggregates their metrics; the in-sample optimization hook is left as a
clearly marked extension point.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from tradingbot.backtest.engine import BacktestRunner
from tradingbot.backtest.metrics import Metrics, compute_metrics
from tradingbot.config import AppConfig
from tradingbot.data.feed import DataFrameFeed


@dataclass
class WalkForwardResult:
    folds: list[Metrics]
    aggregate: Metrics


def walk_forward(
    config: AppConfig,
    df: pd.DataFrame,
    symbol: str,
    n_folds: int = 4,
) -> WalkForwardResult:
    if n_folds < 1:
        raise ValueError("n_folds must be >= 1")

    fold_size = len(df) // n_folds
    fold_metrics: list[Metrics] = []
    all_curve: list[float] = []
    all_pnls: list[float] = []

    for k in range(n_folds):
        start = k * fold_size
        end = len(df) if k == n_folds - 1 else (k + 1) * fold_size
        window = df.iloc[start:end]
        if len(window) < 40:
            continue

        # EXTENSION POINT: optimize params on an in-sample slice preceding
        # `window` here, then apply them below. Foundation uses fixed params.
        runner = BacktestRunner(config)
        result = runner.run(DataFrameFeed(window, symbol=symbol))
        fold_metrics.append(result.metrics)
        all_curve.extend(result.equity_curve)
        all_pnls.extend(t.pnl for t in result.trades)

    aggregate = compute_metrics(all_curve or [config.risk.starting_capital], all_pnls)
    return WalkForwardResult(folds=fold_metrics, aggregate=aggregate)
