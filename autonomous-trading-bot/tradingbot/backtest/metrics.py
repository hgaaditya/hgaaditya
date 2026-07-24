"""Performance metrics.

Deliberately conservative and drawdown-aware — consistent with the project's
goal of consistency over headline returns. All metrics are computed from the
realized equity curve and the completed round-trip trades, i.e. after costs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class Metrics:
    start_equity: float
    end_equity: float
    total_return: float
    max_drawdown: float
    sharpe: float
    num_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    expectancy: float

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def _max_drawdown(equity: list[float]) -> float:
    peak = -math.inf
    mdd = 0.0
    for e in equity:
        peak = max(peak, e)
        if peak > 0:
            mdd = min(mdd, (e - peak) / peak)
    return mdd  # negative fraction, e.g. -0.03


def _sharpe(equity: list[float], periods_per_year: int = 252 * 375) -> float:
    """Annualized Sharpe from per-bar returns (per-minute bars by default)."""
    if len(equity) < 3:
        return 0.0
    rets = [(equity[i] / equity[i - 1] - 1.0) for i in range(1, len(equity)) if equity[i - 1] > 0]
    if not rets:
        return 0.0
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1) if len(rets) > 1 else 0.0
    std = math.sqrt(var)
    if std == 0:
        return 0.0
    return (mean / std) * math.sqrt(periods_per_year)


def compute_metrics(equity_curve: list[float], trade_pnls: list[float]) -> Metrics:
    start = equity_curve[0] if equity_curve else 0.0
    end = equity_curve[-1] if equity_curve else 0.0
    total_return = (end / start - 1.0) if start > 0 else 0.0

    wins = [p for p in trade_pnls if p > 0]
    losses = [p for p in trade_pnls if p <= 0]
    n = len(trade_pnls)
    win_rate = len(wins) / n if n else 0.0
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    gross_profit = sum(wins)
    gross_loss = -sum(losses)
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (math.inf if gross_profit > 0 else 0.0)
    expectancy = (sum(trade_pnls) / n) if n else 0.0

    return Metrics(
        start_equity=start,
        end_equity=end,
        total_return=total_return,
        max_drawdown=_max_drawdown(equity_curve),
        sharpe=_sharpe(equity_curve),
        num_trades=n,
        win_rate=win_rate,
        avg_win=avg_win,
        avg_loss=avg_loss,
        profit_factor=profit_factor,
        expectancy=expectancy,
    )
