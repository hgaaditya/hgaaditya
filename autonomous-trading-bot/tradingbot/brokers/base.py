"""BrokerAdapter interface.

Every broker — paper, Angel One, Zerodha, ccxt, Alpaca — implements this small
surface. The engine only ever talks to this interface, so switching venues (or
switching from paper to live) is a one-line change in the session wiring.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from tradingbot.core.events import Fill, Order, Position


class BrokerAdapter(ABC):
    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def place_order(self, order: Order, ref_price: float) -> Fill:
        """Submit an order. `ref_price` is the current market price used by
        simulated brokers to compute a fill; live brokers ignore it."""

    @abstractmethod
    def positions(self) -> dict[str, Position]: ...

    @abstractmethod
    def funds(self) -> float:
        """Free cash available."""

    @abstractmethod
    def equity(self, marks: dict[str, float]) -> float:
        """Cash + mark-to-market value of open positions."""
