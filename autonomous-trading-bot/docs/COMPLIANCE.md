# Compliance & Risk

> This document is engineering guidance, **not legal advice**. Rules change;
> verify the current SEBI circulars and your broker's algo policy before trading
> live. You are responsible for your own regulatory compliance.

## Risk disclaimer

This is trading software that can place real orders with real money. **No
configuration guarantees profit. You can lose money, potentially more than
expected in fast markets.** The claim that a bot performs "equally well in bull
and bear markets with consistent margins" is **not achievable** and is not what
this project promises. What it is built for is **capital preservation and
controlled drawdown** — losing small and surviving — which is the only durable
basis for consistency. The default runtime is **paper (simulated)**.

## SEBI algo-trading framework (India)

SEBI's February 2025 circular on retail participation in algorithmic trading
introduced requirements that are **fully mandatory from 1 April 2026**. The
practical implications for a bot like this:

- **Broker-registered, tagged strategies.** Algos that place orders via API must
  be registered with, approved by, and tagged through your broker; algo providers
  cannot connect directly to the exchange. Each order carries an algo tag (the
  `Order.tag` field is where this goes).
- **Whitelisted static IP.** API access for retail algos must originate from a
  static IP registered with the broker.
- **Two-factor authentication** on API access.
- **Order-rate thresholds.** Above a per-second order threshold, additional
  registration/controls apply. Keep the bot well under limits; the risk engine's
  position caps help.

Because of this, **live mode is hard-gated in the code**:

- `orchestrator/session.py` raises if `mode: live` is requested in this build.
- `brokers/angelone.py` refuses to connect or trade unless both
  `algo_registered=True` and `static_ip_whitelisted=True` are explicitly set —
  and those flags must only be set after you have genuinely completed broker
  onboarding.

Do not remove these gates to "just try it." Trading an unregistered algo can put
your broking account at risk and may breach regulations.

## Go-live checklist (Phase 2)

Before flipping to live capital, all of the following must be true:

- [ ] Broker account approved for API/algo trading; strategy registered & tagged.
- [ ] Static IP whitelisted with the broker; 2FA configured.
- [ ] `AngelOneBroker` (or your adapter) implemented and reconciliation tested.
- [ ] Weeks of paper soak-testing with acceptable, *stable* out-of-sample metrics.
- [ ] Risk limits set conservatively (small `starting_capital`, tight
      `daily_max_loss`, low `risk_per_trade`).
- [ ] Kill-switch verified against the live broker (it can actually flatten).
- [ ] Alerting on halts, reconciliation breaks, and connectivity loss.
- [ ] You have read and accept that you may lose the deployed capital.

## Other markets

For non-Indian venues (US via `alpaca-py`, crypto via `ccxt`, forex), the SEBI
rules above do not apply, but **that venue's own rules do**. Implement the
equivalent compliance gate in the corresponding adapter before enabling live
trading there.
