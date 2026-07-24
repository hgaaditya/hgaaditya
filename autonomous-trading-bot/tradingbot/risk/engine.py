"""The risk engine — mandatory gatekeeper for every order.

Consistency in trading comes from capital preservation, not from prediction, so
this module is the most important one in the system. Nothing reaches the broker
without passing `check`. It enforces:

  * volatility-aware position sizing (risk a fixed fraction of equity per trade,
    derived from the stop distance);
  * a cap on concurrent positions and on gross exposure;
  * a hard daily loss limit that trips a kill-switch: once tripped, no new entries
    are allowed and the engine asks the caller to flatten everything for the day;
  * an optional daily profit target that also halts trading (bank the good day).

The kill-switch is the single feature most responsible for "lose small and
survive". It is unit-tested.
"""

from __future__ import annotations

from tradingbot.config import RiskConfig
from tradingbot.core.events import Direction, RiskDecision, Signal
from tradingbot.data.universe import get_instrument


class RiskEngine:
    def __init__(self, cfg: RiskConfig):
        self.cfg = cfg
        self.day_start_equity = cfg.starting_capital
        self._halted = False
        self._halt_reason = ""

    # ---- daily lifecycle -------------------------------------------------
    def start_day(self, equity: float) -> None:
        self.day_start_equity = equity
        self._halted = False
        self._halt_reason = ""

    @property
    def halted(self) -> bool:
        return self._halted

    @property
    def halt_reason(self) -> str:
        return self._halt_reason

    def update_equity(self, equity: float) -> bool:
        """Feed current equity; trips the kill-switch if limits are breached.

        Returns True if trading is (now) halted for the day.
        """
        pnl_frac = (equity - self.day_start_equity) / max(self.day_start_equity, 1e-9)
        if pnl_frac <= -self.cfg.daily_max_loss:
            self._trip(f"daily loss limit hit ({pnl_frac:.2%})")
        elif self.cfg.daily_profit_target and pnl_frac >= self.cfg.daily_profit_target:
            self._trip(f"daily profit target hit ({pnl_frac:.2%})")
        return self._halted

    def _trip(self, reason: str) -> None:
        self._halted = True
        self._halt_reason = reason

    # ---- sizing & gating -------------------------------------------------
    def size(self, signal: Signal, ref_price: float, equity: float) -> int:
        """Quantity such that a stop-out loses ~risk_per_trade of equity."""
        if signal.stop_loss is None:
            return 0
        risk_per_unit = abs(ref_price - signal.stop_loss)
        if risk_per_unit <= 0:
            return 0
        rupees_at_risk = equity * self.cfg.risk_per_trade
        raw_qty = int(rupees_at_risk / risk_per_unit)

        lot = get_instrument(signal.symbol).lot_size
        qty = (raw_qty // lot) * lot if lot > 1 else raw_qty
        return max(0, min(qty, self.cfg.per_trade_max_qty))

    def check(
        self,
        signal: Signal,
        ref_price: float,
        equity: float,
        open_positions: int,
        gross_exposure: float,
    ) -> RiskDecision:
        """Approve/resize/reject a proposed entry."""
        if self._halted:
            return RiskDecision(False, f"halted: {self._halt_reason}")
        if signal.direction is Direction.FLAT:
            return RiskDecision(True, "flatten", qty=0, stop_loss=signal.stop_loss)

        if open_positions >= self.cfg.max_positions:
            return RiskDecision(False, "max concurrent positions reached")

        qty = self.size(signal, ref_price, equity)
        if qty <= 0:
            return RiskDecision(False, "sized to zero (stop too wide or no stop)")

        added_exposure = qty * ref_price
        if (gross_exposure + added_exposure) > self.cfg.max_exposure * equity:
            # Shrink to fit remaining exposure budget.
            budget = self.cfg.max_exposure * equity - gross_exposure
            qty = int(budget / ref_price)
            lot = get_instrument(signal.symbol).lot_size
            qty = (qty // lot) * lot if lot > 1 else qty
            if qty <= 0:
                return RiskDecision(False, "no exposure budget remaining")

        return RiskDecision(True, "approved", qty=qty, stop_loss=signal.stop_loss)
