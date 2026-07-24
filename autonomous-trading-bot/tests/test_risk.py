from datetime import datetime

from tradingbot.config import RiskConfig
from tradingbot.core.events import Direction, Signal
from tradingbot.risk.engine import RiskEngine


def _sig(stop):
    return Signal("RELIANCE", datetime(2026, 1, 5, 9, 30), Direction.LONG, 0.8, "trend",
                  stop_loss=stop, target=None)


def test_sizing_respects_risk_per_trade():
    cfg = RiskConfig(starting_capital=100_000, risk_per_trade=0.01)
    eng = RiskEngine(cfg)
    # Stop 10 rupees away, risking 1% of 100k = 1000 -> qty ~ 100.
    qty = eng.size(_sig(stop=90.0), ref_price=100.0, equity=100_000)
    assert qty == 100


def test_no_stop_sizes_to_zero():
    eng = RiskEngine(RiskConfig())
    s = Signal("X", datetime(2026, 1, 5), Direction.LONG, 0.5, "t", stop_loss=None)
    assert eng.size(s, 100.0, 100_000) == 0


def test_kill_switch_trips_and_blocks_entries():
    cfg = RiskConfig(starting_capital=100_000, daily_max_loss=0.02)
    eng = RiskEngine(cfg)
    eng.start_day(100_000)
    assert not eng.update_equity(99_000)   # -1% ok
    assert eng.update_equity(97_900)       # -2.1% -> halt
    assert eng.halted
    decision = eng.check(_sig(90.0), 100.0, 97_900, 0, 0.0)
    assert not decision.approved and "halted" in decision.reason


def test_max_positions_blocks():
    cfg = RiskConfig(max_positions=1)
    eng = RiskEngine(cfg)
    eng.start_day(100_000)
    decision = eng.check(_sig(90.0), 100.0, 100_000, open_positions=1, gross_exposure=0.0)
    assert not decision.approved
