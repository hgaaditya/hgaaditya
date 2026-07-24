"""Domain events and value objects shared across the whole system.

These are the *only* types that flow between the data feed, strategies, the
risk engine, the order manager, and brokers. Keeping them small and explicit is
what lets backtest, paper, and live share one code path.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

    @property
    def sign(self) -> int:
        return 1 if self is Side.BUY else -1


class Direction(str, Enum):
    """What a strategy wants the net position in a symbol to be."""

    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"  # close any open position


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderStatus(str, Enum):
    NEW = "NEW"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class Regime(str, Enum):
    """Market regime used to pick which strategy is allowed to act."""

    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    RANGE = "RANGE"
    HIGH_VOL = "HIGH_VOL"
    UNKNOWN = "UNKNOWN"


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass(frozen=True)
class Bar:
    """A single OHLCV candle for one instrument."""

    symbol: str
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    timeframe: str = "1m"


@dataclass
class Signal:
    """A strategy's intent. `stop_loss`/`target` are absolute prices."""

    symbol: str
    ts: datetime
    direction: Direction
    strength: float  # 0..1 conviction
    strategy: str
    reason: str = ""
    stop_loss: float | None = None
    target: float | None = None


@dataclass
class Order:
    symbol: str
    side: Side
    qty: int
    order_type: OrderType
    ts: datetime
    limit_price: float | None = None
    product: str = "MIS"  # MIS = intraday on Indian exchanges
    tag: str = ""  # SEBI algo tagging goes here in live mode
    id: str = field(default_factory=_new_id)
    status: OrderStatus = OrderStatus.NEW


@dataclass
class Fill:
    order_id: str
    symbol: str
    side: Side
    qty: int
    price: float
    ts: datetime
    commission: float = 0.0
    taxes: float = 0.0
    slippage: float = 0.0

    @property
    def cost(self) -> float:
        """Total frictional cost of the fill (charges + slippage value)."""
        return self.commission + self.taxes + self.slippage * self.qty


@dataclass
class Position:
    symbol: str
    qty: int = 0  # signed: +long, -short
    avg_price: float = 0.0
    realized_pnl: float = 0.0

    @property
    def is_flat(self) -> bool:
        return self.qty == 0

    def unrealized(self, mark: float) -> float:
        return self.qty * (mark - self.avg_price)


@dataclass
class RiskDecision:
    approved: bool
    reason: str
    qty: int = 0
    stop_loss: float | None = None
