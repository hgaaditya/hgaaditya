"""Angel One SmartAPI adapter — Phase 2 live execution (stub).

The interface is complete and matches BrokerAdapter; the live calls are gated
behind a hard compliance check because SEBI's 2025 algo framework requires the
strategy to be registered/tagged through the broker and run from a whitelisted
static IP. Do not remove that gate. See docs/COMPLIANCE.md.

To implement: `pip install '.[angelone]'`, then fill in the marked sections with
smartapi-python calls (SmartConnect: placeOrder, position, rmsLimit, and the
websocket feed wired into a DataFeed).
"""

from __future__ import annotations

from tradingbot.brokers.base import BrokerAdapter
from tradingbot.core.events import Fill, Order, Position


class ComplianceError(RuntimeError):
    pass


class AngelOneBroker(BrokerAdapter):
    def __init__(
        self,
        api_key: str,
        client_id: str,
        pin: str,
        totp_secret: str,
        *,
        algo_registered: bool = False,
        static_ip_whitelisted: bool = False,
    ):
        self.api_key = api_key
        self.client_id = client_id
        self._pin = pin
        self._totp_secret = totp_secret
        self.algo_registered = algo_registered
        self.static_ip_whitelisted = static_ip_whitelisted
        self._client = None

    def _require_compliance(self) -> None:
        if not (self.algo_registered and self.static_ip_whitelisted):
            raise ComplianceError(
                "Live trading blocked: SEBI 2025 algo rules require a broker-"
                "registered/tagged strategy AND a whitelisted static IP. "
                "Set algo_registered=True and static_ip_whitelisted=True only "
                "after completing broker onboarding (see docs/COMPLIANCE.md)."
            )

    def connect(self) -> None:
        self._require_compliance()
        raise NotImplementedError(
            "AngelOneBroker.connect: install '.[angelone]' and wire SmartConnect."
        )

    def place_order(self, order: Order, ref_price: float) -> Fill:  # noqa: ARG002
        self._require_compliance()
        raise NotImplementedError("AngelOneBroker.place_order not implemented (Phase 2).")

    def positions(self) -> dict[str, Position]:
        raise NotImplementedError("AngelOneBroker.positions not implemented (Phase 2).")

    def funds(self) -> float:
        raise NotImplementedError("AngelOneBroker.funds not implemented (Phase 2).")

    def equity(self, marks: dict[str, float]) -> float:  # noqa: ARG002
        raise NotImplementedError("AngelOneBroker.equity not implemented (Phase 2).")
