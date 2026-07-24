"""Command-line interface.

    tradingbot backtest --symbol RELIANCE --days 5
    tradingbot run --symbol RELIANCE --days 1       # paper session (replayed)
    tradingbot walkforward --symbol RELIANCE --days 8 --folds 4
    tradingbot version

By default it uses the deterministic synthetic generator so everything runs with
no external data or broker. Pass --csv to use your own OHLCV file.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import typer

from tradingbot import __version__
from tradingbot.audit.reporter import print_metrics, summary_line
from tradingbot.backtest.engine import BacktestRunner
from tradingbot.backtest.walkforward import walk_forward
from tradingbot.config import AppConfig
from tradingbot.data.feed import DataFrameFeed
from tradingbot.data.synthetic import generate_days
from tradingbot.logging_setup import setup_logging
from tradingbot.orchestrator.scheduler import run_paper_session

app = typer.Typer(add_completion=False, help="Autonomous risk-first trading bot (Indian market).")


def _load_config(config: str | None, capital: float | None) -> AppConfig:
    cfg = AppConfig.load(config)
    if capital is not None:
        cfg.risk.starting_capital = capital
    return cfg


def _load_df(csv: str | None, symbol: str, days: int, regime: str, seed: int) -> pd.DataFrame:
    if csv:
        return pd.read_csv(csv, parse_dates=[0], index_col=0).sort_index()
    return generate_days(symbol=symbol, days=days, regime=regime, seed=seed)


def _read_headlines(path: str | None) -> list[str] | None:
    if not path:
        return None
    return [ln.strip() for ln in Path(path).read_text().splitlines() if ln.strip()]


@app.command()
def backtest(
    symbol: str = typer.Option("RELIANCE", help="Instrument symbol"),
    days: int = typer.Option(5, help="Number of synthetic sessions"),
    regime: str = typer.Option("mixed", help="mixed|bull|bear|flat (synthetic only)"),
    seed: int = typer.Option(7, help="Synthetic RNG seed (reproducible)"),
    capital: float = typer.Option(None, help="Override starting capital"),
    csv: str = typer.Option(None, help="Path to your own OHLCV CSV instead of synthetic"),
    config: str = typer.Option(None, help="Path to a YAML config"),
):
    """Run a backtest over the real engine and print a metrics report."""
    cfg = _load_config(config, capital)
    df = _load_df(csv, symbol, days, regime, seed)
    result = BacktestRunner(cfg).run(DataFrameFeed(df, symbol=symbol))
    print_metrics(result.metrics, title=f"Backtest {result.run_id} [{symbol}]")
    typer.echo(f"audit chain verified: {result.chain_ok}")


@app.command()
def run(
    symbol: str = typer.Option("RELIANCE"),
    days: int = typer.Option(1, help="Sessions to replay as if live"),
    regime: str = typer.Option("mixed"),
    seed: int = typer.Option(7),
    capital: float = typer.Option(None),
    headlines: str = typer.Option(None, help="Text file, one headline per line (sentiment)"),
    csv: str = typer.Option(None),
    config: str = typer.Option(None),
):
    """Run a paper-trading session (replayed) end-to-end with logging + audit."""
    cfg = _load_config(config, capital)
    cfg.mode = "paper"
    df = _load_df(csv, symbol, days, regime, seed)
    run_id, metrics = run_paper_session(cfg, df, symbol, headlines=_read_headlines(headlines))
    typer.echo(f"run_id={run_id}  {summary_line(metrics)}")


@app.command()
def walkforward(
    symbol: str = typer.Option("RELIANCE"),
    days: int = typer.Option(8),
    folds: int = typer.Option(4),
    seed: int = typer.Option(7),
    capital: float = typer.Option(None),
    config: str = typer.Option(None),
):
    """Walk-forward evaluation (out-of-sample aggregate is what matters)."""
    cfg = _load_config(config, capital)
    df = generate_days(symbol=symbol, days=days, regime="mixed", seed=seed)
    res = walk_forward(cfg, df, symbol, n_folds=folds)
    for i, m in enumerate(res.folds):
        typer.echo(f"  fold {i}: {summary_line(m)}")
    print_metrics(res.aggregate, title="Walk-forward aggregate (out-of-sample)")


@app.command()
def version():
    """Print version."""
    setup_logging()
    typer.echo(f"tradingbot {__version__}")


if __name__ == "__main__":
    app()
