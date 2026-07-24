# Roadmap

The goal is a **fully autonomous, self-improving** intraday bot. That is built in
phases, risk-first, so that at every stage the system is safe, observable, and
honestly evaluated. Live money comes only after the machinery has proven itself
on paper.

## Phase 1 — Foundation ✅ (this build)

Everything running end-to-end in simulation:

- Broker-agnostic architecture; **PaperBroker** default runtime.
- Two baseline strategies (trend, mean-reversion) + **regime classifier** that
  selects between them.
- **Risk engine**: volatility-based sizing, exposure caps, **daily kill-switch**.
- Realistic **Indian cost model** (brokerage, STT, exchange, SEBI, stamp, GST,
  slippage).
- **Backtester** and **walk-forward** evaluation sharing the live code path.
- Structured logging + **tamper-evident SQLite audit trail**.
- Pluggable **sentiment** (rule-based default, Claude-API adapter).
- CLI, tests (incl. golden regression + kill-switch + audit-chain), docs.

## Phase 2 — Live execution (compliant)

- Implement `AngelOneBroker` (or your chosen broker) against `BrokerAdapter`:
  auth/2FA, order placement, position/funds sync, websocket feed → `DataFeed`.
- **Reconciliation**: continuously reconcile the bot's expected positions/cash
  with the broker's truth; halt on divergence.
- **Compliance gates** (see `COMPLIANCE.md`): broker algo registration/tagging,
  whitelisted static IP, order-rate limits. The live path stays hard-gated until
  these are satisfied.
- Extended **paper soak test** (weeks) before any real capital.
- Small live capital with tight hard limits; manual promotion only.

## Phase 3 — Self-learning loop (governed)

The "self-improving" part — deliberately governed to avoid overfitting to noise:

- Track live performance per strategy/parameter set in the journal.
- Periodic **walk-forward re-validation**; only promote a configuration whose
  *out-of-sample* aggregate beats the incumbent by a margin.
- **Parameter optimization** with guardrails (parameter stability, minimum trade
  count, drawdown ceilings) — never optimize on the most recent window alone.
- **Drift monitoring**: detect when live behaviour diverges from backtest
  assumptions and fall back to a conservative default (or stand aside).
- Champion/challenger: challengers run in paper alongside the live champion and
  are promoted only after sustained out-of-sample edge.

## Phase 4 — Breadth

- More strategies (breakout, VWAP-reversion, pairs) and an options module
  (greeks, IV-aware sizing).
- Commodities (MCX), and non-Indian venues via `ccxt` (crypto) and `alpaca-py`
  (US) — the adapter interface already supports them.
- Richer sentiment: live news/RSS ingestion, macro/event calendar, LLM analysis
  with the bounded-score contract kept intact.
- Optional dashboard over the journal (equity curve, live positions, audit view).

## Non-negotiables across all phases

- The **risk engine is never bypassed**.
- **No live order** without passing the compliance gate.
- Every configuration change is **backtested and walk-forward validated** before
  it can trade live.
- The **audit chain** is always on.
