"""Human-readable reporting over a run's journal / backtest result."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from tradingbot.backtest.metrics import Metrics

_console = Console()


def _fmt(v: float, pct: bool = False) -> str:
    if pct:
        return f"{v:+.2%}"
    return f"{v:,.2f}"


def print_metrics(metrics: Metrics, title: str = "Backtest Report") -> None:
    t = Table(title=title, show_header=True, header_style="bold")
    t.add_column("Metric")
    t.add_column("Value", justify="right")

    rows = [
        ("Start equity", _fmt(metrics.start_equity)),
        ("End equity", _fmt(metrics.end_equity)),
        ("Total return", _fmt(metrics.total_return, pct=True)),
        ("Max drawdown", _fmt(metrics.max_drawdown, pct=True)),
        ("Sharpe (annualized)", _fmt(metrics.sharpe)),
        ("Trades", str(metrics.num_trades)),
        ("Win rate", _fmt(metrics.win_rate, pct=True)),
        ("Avg win", _fmt(metrics.avg_win)),
        ("Avg loss", _fmt(metrics.avg_loss)),
        ("Profit factor", _fmt(metrics.profit_factor)),
        ("Expectancy / trade", _fmt(metrics.expectancy)),
    ]
    for k, v in rows:
        t.add_row(k, v)
    _console.print(t)


def summary_line(metrics: Metrics) -> str:
    return (
        f"return={metrics.total_return:+.2%} maxDD={metrics.max_drawdown:.2%} "
        f"sharpe={metrics.sharpe:.2f} trades={metrics.num_trades} "
        f"win={metrics.win_rate:.0%} PF={metrics.profit_factor:.2f}"
    )
