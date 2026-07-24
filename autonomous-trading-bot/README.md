# Autonomous Trading Bot

A **risk-first, self-improving intraday trading bot**. Indian market first
(NSE/BSE — stocks, indices, commodities), architected to extend to foreign
equities, forex, and crypto. Runs locally, is seeded with capital, and then runs
the full pipeline on its own: **regime detection → strategy selection → risk-gated
execution → logging → tamper-evident auditing → backtesting.**

> ⚠️ **Read first:** This is trading software with real financial risk. **No
> configuration guarantees profit.** The default runtime is **paper** (simulated).
> Live trading in India requires a SEBI-compliant, broker-registered algo and a
> whitelisted static IP — see [`docs/COMPLIANCE.md`](docs/COMPLIANCE.md). Nothing
> here is financial advice.

## Design philosophy

Consistency in trading comes from **capital preservation, not prediction**. The
bot is built to *lose small and survive* first, be profitable second:

- **The risk engine is a mandatory gatekeeper** — every order passes through it.
  Volatility-based position sizing, exposure caps, and a **hard daily-loss
  kill-switch** that flattens and halts for the day.
- **One code path for backtest, paper, and live.** Strategies/risk/execution are
  written once; only the data feed and broker adapter swap. So a backtest
  reflects what live would actually have done — see [`tradingbot/engine.py`](tradingbot/engine.py).
- **The regime classifier decides which strategy acts** (trend vs. mean-reversion
  vs. stand-aside), instead of pretending one strategy is all-weather.
- **Everything is audited.** A SQLite journal records every signal, risk
  decision, order, fill, and equity mark, with a **SHA-256 hash chain** that makes
  after-the-fact tampering detectable.

## Quick start

```bash
cd autonomous-trading-bot
uv venv --python 3.11 .venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Backtest over deterministic synthetic data (no broker/data needed):
tradingbot backtest --symbol RELIANCE --days 5

# Run a paper session end-to-end (logging + audit written to runs/):
tradingbot run --symbol RELIANCE --days 1

# Walk-forward evaluation (out-of-sample aggregate is the number that matters):
tradingbot walkforward --symbol RELIANCE --days 8 --folds 4

pytest        # full test suite incl. golden backtest + kill-switch + audit-chain
```

Use your own data with `--csv path.csv` (first column datetime index; columns
`open,high,low,close,volume`). Configure everything via `configs/default.yaml`
and `--config`.

> **Note on symbols:** the demo uses `RELIANCE` (lot size 1) so position sizing
> is clean on ₹1 lakh. Index/derivative instruments like `NIFTY` have large lot
> sizes and notionals — trading them needs proportionally more capital (or
> futures margin) or the risk engine will (correctly) size orders to zero. Set
> `starting_capital` accordingly.

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full data flow and
extension points, and [`docs/ROADMAP.md`](docs/ROADMAP.md) for the path from this
foundation to live trading and the self-learning loop.

```
data feed → engine ┬→ regime classifier → strategy → Signal
                   │→ risk engine (size/gate/kill-switch) → Order
                   │→ broker (paper|live) → Fill
                   └→ journal (structured logs + hash-chained audit)
```

## Status

**Phase 1 (this build): foundation.** Paper trading + backtesting + risk engine +
audit + two baseline strategies + regime classifier + pluggable sentiment, all
running end-to-end in simulation. Live execution (Phase 2), the self-learning
loop (Phase 3), and broader markets (Phase 4) are scaffolded with clear
interfaces — see the roadmap.

## License

MIT.
