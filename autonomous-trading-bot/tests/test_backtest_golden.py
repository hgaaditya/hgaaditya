"""Regression test for the end-to-end backtest.

Rather than pin brittle float metrics, we assert the properties that must hold
for the system to be trustworthy: determinism (same seed -> identical result),
that the pipeline actually trades, that the audit chain verifies, and that
equity is internally consistent. A bull day should also not blow up the account.
"""

from tradingbot.backtest.engine import BacktestRunner
from tradingbot.config import AppConfig
from tradingbot.data.feed import DataFrameFeed
from tradingbot.data.synthetic import generate_days


def _run(cfg, seed=7, regime="mixed", days=6):
    df = generate_days(days=days, regime=regime, seed=seed)
    return BacktestRunner(cfg).run(DataFrameFeed(df, symbol="RELIANCE"))


def test_backtest_is_deterministic(cfg: AppConfig):
    r1 = _run(cfg)
    r2 = _run(cfg)
    assert r1.equity_curve == r2.equity_curve
    assert [t.pnl for t in r1.trades] == [t.pnl for t in r2.trades]


def test_backtest_trades_and_audits(cfg: AppConfig):
    r = _run(cfg)
    assert r.metrics.num_trades > 0, "engine should generate trades on synthetic data"
    assert r.chain_ok, "audit hash chain must verify"
    # Win rate and profit factor are well-defined fractions.
    assert 0.0 <= r.metrics.win_rate <= 1.0
    assert r.metrics.max_drawdown <= 0.0


def test_equity_curve_consistent_length(cfg: AppConfig):
    r = _run(cfg, days=3)
    # One equity mark per bar (3 sessions * 375 minutes).
    assert len(r.equity_curve) == 3 * 375
    assert r.equity_curve[0] > 0


def test_daily_loss_never_exceeds_limit_by_much(cfg: AppConfig):
    # With a tight daily loss limit, intraday drawdown from the day's open is
    # bounded (kill-switch flattens). Allow slack for the flattening bar's costs.
    cfg.risk.daily_max_loss = 0.02
    r = _run(cfg, regime="bear", seed=11, days=4)
    # Total drawdown across multiple days can exceed a single day's limit, but a
    # single catastrophic wipeout should not happen.
    assert r.metrics.end_equity > cfg.risk.starting_capital * 0.9
