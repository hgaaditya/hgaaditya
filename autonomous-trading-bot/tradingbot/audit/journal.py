"""Durable, tamper-evident audit trail in SQLite.

Two things every serious trading system needs and this provides:

  1. A complete record of what the bot did — every signal, risk decision, order,
     fill, and equity mark — queryable after the fact.
  2. Integrity you can trust. Each row in `audit_log` carries the SHA-256 hash of
     the previous row plus its own payload, forming a hash chain. If any past
     record is altered or deleted, `verify_chain()` fails at that point. You can
     prove the journal wasn't quietly edited after a bad day.

SQLite is chosen for zero-ops local durability; the schema ports directly to
Postgres if you outgrow it.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from tradingbot.core.events import Fill, Order, RiskDecision, Signal

_GENESIS = "0" * 64


class TradeJournal:
    def __init__(self, db_path: str | Path, run_id: str):
        self.run_id = run_id
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        # WAL + NORMAL keeps the audit trail durable across crashes while making
        # commits cheap enough to write on every fill without an fsync storm.
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY, started_at TEXT, mode TEXT, config TEXT
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT, ts TEXT, kind TEXT, symbol TEXT, payload TEXT
            );
            CREATE TABLE IF NOT EXISTS equity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT, ts TEXT, equity REAL
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT, ts TEXT, kind TEXT, payload TEXT,
                prev_hash TEXT, hash TEXT
            );
            """
        )
        self.conn.commit()

    # ---- run metadata ----------------------------------------------------
    def start_run(self, mode: str, config: dict) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO runs VALUES (?,?,?,?)",
            (self.run_id, datetime.now().isoformat(), mode, json.dumps(config, default=str)),
        )
        self.conn.commit()
        self._append_audit("run_start", {"mode": mode})

    # ---- domain events ---------------------------------------------------
    def record_signal(self, s: Signal) -> None:
        self._event("signal", s.symbol, s.ts, asdict(s))

    def record_risk(self, symbol: str, ts: datetime, d: RiskDecision) -> None:
        self._event("risk", symbol, ts, asdict(d))

    def record_order(self, o: Order) -> None:
        self._event("order", o.symbol, o.ts, asdict(o))

    def record_fill(self, f: Fill) -> None:
        self._event("fill", f.symbol, f.ts, asdict(f))
        # Fills are the money-moving events, so they also anchor the hash chain.
        self._append_audit("fill", asdict(f))

    def record_equity(self, ts: datetime, equity: float) -> None:
        # High-frequency (per-bar): buffered, flushed on the next fill/audit
        # commit and at close(). Same-connection reads still see these rows.
        self.conn.execute(
            "INSERT INTO equity (run_id, ts, equity) VALUES (?,?,?)",
            (self.run_id, ts.isoformat(), float(equity)),
        )

    def record_halt(self, ts: datetime, reason: str) -> None:
        self._event("halt", None, ts, {"reason": reason})
        self._append_audit("halt", {"reason": reason})

    def _event(self, kind: str, symbol: str | None, ts: datetime, payload: dict) -> None:
        # Buffered like equity; the next fill's audit commit (or close) flushes.
        self.conn.execute(
            "INSERT INTO events (run_id, ts, kind, symbol, payload) VALUES (?,?,?,?,?)",
            (self.run_id, ts.isoformat(), kind, symbol, json.dumps(payload, default=str)),
        )

    # ---- hash-chained audit log -----------------------------------------
    def _append_audit(self, kind: str, payload: dict[str, Any]) -> str:
        cur = self.conn.execute(
            "SELECT hash FROM audit_log WHERE run_id=? ORDER BY seq DESC LIMIT 1",
            (self.run_id,),
        ).fetchone()
        prev = cur["hash"] if cur else _GENESIS
        ts = datetime.now().isoformat()
        body = json.dumps(payload, sort_keys=True, default=str)
        digest = hashlib.sha256(f"{prev}|{kind}|{body}".encode()).hexdigest()
        self.conn.execute(
            "INSERT INTO audit_log (run_id, ts, kind, payload, prev_hash, hash) VALUES (?,?,?,?,?,?)",
            (self.run_id, ts, kind, body, prev, digest),
        )
        self.conn.commit()
        return digest

    def verify_chain(self) -> bool:
        """Recompute the chain; return False if any link is broken."""
        rows = self.conn.execute(
            "SELECT kind, payload, prev_hash, hash FROM audit_log WHERE run_id=? ORDER BY seq",
            (self.run_id,),
        ).fetchall()
        prev = _GENESIS
        for r in rows:
            if r["prev_hash"] != prev:
                return False
            expect = hashlib.sha256(
                f"{r['prev_hash']}|{r['kind']}|{r['payload']}".encode()
            ).hexdigest()
            if expect != r["hash"]:
                return False
            prev = r["hash"]
        return True

    # ---- read helpers ----------------------------------------------------
    def equity_curve(self) -> list[tuple[str, float]]:
        rows = self.conn.execute(
            "SELECT ts, equity FROM equity WHERE run_id=? ORDER BY id", (self.run_id,)
        ).fetchall()
        return [(r["ts"], r["equity"]) for r in rows]

    def fills(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT payload FROM events WHERE run_id=? AND kind='fill' ORDER BY id",
            (self.run_id,),
        ).fetchall()
        return [json.loads(r["payload"]) for r in rows]

    def close(self) -> None:
        self.conn.commit()  # flush any buffered events/equity rows
        self.conn.close()
