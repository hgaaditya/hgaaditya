"""PaperBroker — the default runtime and the simulation core of the backtester.

Holds cash and positions, fills market orders at the reference price adjusted for
slippage, and books realistic Indian charges via CostModel. It is the single
source of truth for portfolio state in both backtest and paper modes, which is
exactly why backtest results are representative of paper behaviour.
"""

from __future__ import annotations

from tradingbot.brokers.base import BrokerAdapter
from tradingbot.brokers.costs import CostModel
from tradingbot.config import CostConfig
from tradingbot.core.events import Fill, Order, OrderStatus, Position, Side


class PaperBroker(BrokerAdapter):
    def __init__(self, starting_cash: float, costs: CostConfig | None = None):
        self._cash = starting_cash
        self._start_cash = starting_cash
        self._positions: dict[str, Position] = {}
        self.costs = CostModel(costs or CostConfig())
        self.fills: list[Fill] = []

    def connect(self) -> None:  # nothing to do for a simulated broker
        return None

    def funds(self) -> float:
        return self._cash

    def positions(self) -> dict[str, Position]:
        return {s: p for s, p in self._positions.items() if not p.is_flat}

    def position(self, symbol: str) -> Position:
        return self._positions.setdefault(symbol, Position(symbol))

    def equity(self, marks: dict[str, float]) -> float:
        eq = self._cash
        for sym, pos in self._positions.items():
            if not pos.is_flat and sym in marks:
                eq += pos.qty * marks[sym]
        return eq

    def place_order(self, order: Order, ref_price: float) -> Fill:
        fill_price = self.costs.slippage_price(order.side, ref_price)
        charges = self.costs.charges(order.side, order.qty, fill_price)
        slip = abs(fill_price - ref_price)

        self._apply_fill(order.symbol, order.side, order.qty, fill_price, charges)

        order.status = OrderStatus.FILLED
        fill = Fill(
            order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            qty=order.qty,
            price=fill_price,
            ts=order.ts,
            commission=0.0,
            taxes=charges,
            slippage=slip,
        )
        self.fills.append(fill)
        return fill

    def _apply_fill(
        self, symbol: str, side: Side, qty: int, price: float, charges: float
    ) -> None:
        """Update cash and position for a fill, booking realized P&L on reductions."""
        pos = self.position(symbol)
        signed = side.sign * qty  # +buy, -sell

        # Cash: pay for buys, receive for sells; charges always reduce cash.
        self._cash -= side.sign * qty * price
        self._cash -= charges

        old_qty = pos.qty
        new_qty = old_qty + signed

        if old_qty == 0 or (old_qty > 0) == (signed > 0):
            # Opening or increasing in the same direction: blend average price.
            total_cost = pos.avg_price * abs(old_qty) + price * qty
            pos.avg_price = total_cost / abs(new_qty) if new_qty != 0 else 0.0
        else:
            # Reducing / closing / flipping: realize P&L on the closed quantity.
            closed = min(abs(signed), abs(old_qty))
            direction = 1 if old_qty > 0 else -1
            pos.realized_pnl += direction * closed * (price - pos.avg_price)
            if abs(signed) > abs(old_qty):
                # Flipped through zero: remainder opens a new position at price.
                pos.avg_price = price
            elif new_qty == 0:
                pos.avg_price = 0.0
            # else: partial close keeps the same avg_price

        pos.qty = new_qty
