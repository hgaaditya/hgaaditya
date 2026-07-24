"""Backtesting: run the real engine over historical data and score it honestly."""

from tradingbot.backtest.engine import BacktestResult, BacktestRunner
from tradingbot.backtest.metrics import compute_metrics

__all__ = ["BacktestRunner", "BacktestResult", "compute_metrics"]
