from datetime import datetime

from tradingbot.audit.journal import TradeJournal
from tradingbot.core.events import Fill, Side


def _fill(price):
    return Fill("oid", "RELIANCE", Side.BUY, 10, price, datetime(2026, 1, 5, 9, 30),
                taxes=1.0, slippage=0.02)


def test_chain_valid_after_writes(tmp_path):
    j = TradeJournal(tmp_path / "j.sqlite", "run1")
    j.start_run("backtest", {"x": 1})
    for p in (100.0, 101.0, 102.0):
        j.record_fill(_fill(p))
    assert j.verify_chain()
    j.close()


def test_tamper_is_detected(tmp_path):
    db = tmp_path / "j.sqlite"
    j = TradeJournal(db, "run1")
    j.start_run("backtest", {})
    j.record_fill(_fill(100.0))
    j.record_fill(_fill(101.0))
    assert j.verify_chain()
    # Silently rewrite a payload in the audit log -> chain must break.
    j.conn.execute("UPDATE audit_log SET payload='{\"tampered\":true}' WHERE seq=2")
    j.conn.commit()
    assert not j.verify_chain()
    j.close()
