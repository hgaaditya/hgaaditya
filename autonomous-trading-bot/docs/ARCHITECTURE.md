# Architecture

## Guiding principle

**One decision path, swappable edges.** The bot's intelligence — regime
detection, strategy selection, risk gating, execution, auditing — is written
once, in `tradingbot/engine.py`. The only things that change between backtest,
paper, and live are the two *edges*: the **data feed** (where bars come from) and
the **broker adapter** (where orders go). This is the single most important
design choice in the project, because it means a backtest is not a separate
model that can disagree with production — it *is* production, replayed.

```
            ┌─────────────┐        ┌──────────────────────────────┐        ┌──────────────┐
 bars  ───▶ │  DataFeed   │ ─────▶ │        TradingEngine         │ ─────▶ │ BrokerAdapter│
            │ (swappable) │        │  regime → strategy → signal  │        │ (swappable)  │
            └─────────────┘        │  → risk engine → order       │        └──────────────┘
                                   │  → fill → journal            │
                                   └──────────────┬───────────────┘
                                                  ▼
                                        ┌────────────────────┐
                                        │  TradeJournal      │
                                        │  logs + hash-chain │
                                        └────────────────────┘
```

## Per-bar decision flow (`TradingEngine.on_bar`)

1. **Roll day / update history.** Append the bar to a bounded rolling window per
   symbol (only recent bars are needed for indicators).
2. **Mark-to-market.** Compute equity from the broker's positions and record it.
3. **Kill-switch check.** `RiskEngine.update_equity` trips a hard halt if the
   daily loss (or optional profit target) limit is breached.
4. **Square-off / halt.** If halted or past 15:15 IST, flatten everything and
   take no new entries for the rest of the day.
5. **Manage exits.** For an open position, check whether this bar's high/low hit
   the stop or target; if so, close it.
6. **Seek entry (if flat).** Classify the regime, pick the strategy that owns
   that regime, ask it for signals, apply the sentiment gate, size and risk-check
   each signal, and route approved orders to the broker.

Every step writes to the journal (structured JSON log + SQLite), and money-moving
events (fills, halts) are anchored into a SHA-256 hash chain.

## Modules

| Area | Module | Responsibility |
|------|--------|----------------|
| Domain model | `core/events.py` | Bar, Signal, Order, Fill, Position, RiskDecision, enums |
| Indicators | `core/indicators.py` | EMA, RSI, ATR, Bollinger, ADX (pandas-only) |
| Calendar | `core/clock.py` | NSE session hours, square-off, trading days |
| Data | `data/feed.py`, `data/synthetic.py`, `data/universe.py` | feeds, deterministic data, instrument master |
| Brokers | `brokers/base.py`, `brokers/paper.py`, `brokers/angelone.py` | adapter interface, simulation, live stub |
| Costs | `brokers/costs.py` | Indian intraday charges + slippage |
| Strategies | `strategies/trend.py`, `strategies/mean_reversion.py` | signal generation |
| Regime | `regime/classifier.py` | which strategy is allowed to act |
| Sentiment | `sentiment/rules.py`, `sentiment/llm.py` | daily directional bias (pluggable) |
| Risk | `risk/engine.py` | sizing, exposure caps, kill-switch |
| Engine | `engine.py` | the shared per-bar loop |
| Backtest | `backtest/engine.py`, `backtest/metrics.py`, `backtest/walkforward.py` | run + score + validate |
| Audit | `audit/journal.py`, `audit/reporter.py` | tamper-evident trail, reports |
| Orchestration | `orchestrator/session.py`, `orchestrator/scheduler.py` | composition + day schedule |
| CLI | `cli.py` | `backtest`, `run`, `walkforward`, `version` |

## Extension points

- **New broker/market:** implement `BrokerAdapter` (see `brokers/paper.py` as the
  reference). For crypto use `ccxt`, for US equities `alpaca-py`; the engine is
  unchanged.
- **New strategy:** subclass `Strategy`, register it in `strategies/__init__.py`,
  and map a regime to it in `regime/classifier.py`.
- **New sentiment source:** implement `SentimentProvider` (rule-based and Claude
  adapters already exist).
- **Smarter regime detection:** `regime/classifier.py` is intentionally a
  transparent rule-based baseline; a learned classifier can replace it behind the
  same interface, and the Phase-3 loop measures any replacement against it.

## Why these choices

- **pandas-only indicators / synthetic data:** the core installs and tests with
  no native builds and no market-data dependency; results are reproducible.
- **PaperBroker as the simulation core:** backtest and paper share the exact fill
  and cost logic, so there is no "backtest vs reality" gap in the accounting.
- **SQLite + hash chain:** zero-ops local durability plus provable integrity —
  you can demonstrate the journal wasn't edited after a bad day.
