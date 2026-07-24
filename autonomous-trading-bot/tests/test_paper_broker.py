from datetime import datetime

from tradingbot.brokers.paper import PaperBroker
from tradingbot.core.events import Order, OrderType, Side


def _order(symbol, side, qty):
    return Order(symbol, side, qty, OrderType.MARKET, datetime(2026, 1, 5, 9, 30))


def test_buy_then_sell_realizes_pnl_after_costs():
    b = PaperBroker(100_000.0)
    b.place_order(_order("RELIANCE", Side.BUY, 10), ref_price=100.0)
    pos = b.position("RELIANCE")
    assert pos.qty == 10
    # Sell higher; realized pnl should be positive but reduced by charges/slippage.
    b.place_order(_order("RELIANCE", Side.SELL, 10), ref_price=110.0)
    assert b.position("RELIANCE").is_flat
    assert b.position("RELIANCE").realized_pnl > 0
    # Net cash gain must be less than the gross 10*(110-100)=100 due to costs.
    assert 0 < (b.funds() - 100_000.0) < 100.0


def test_short_then_cover():
    b = PaperBroker(100_000.0)
    b.place_order(_order("INFY", Side.SELL, 5), ref_price=200.0)
    assert b.position("INFY").qty == -5
    b.place_order(_order("INFY", Side.BUY, 5), ref_price=190.0)
    assert b.position("INFY").is_flat
    assert b.position("INFY").realized_pnl > 0


def test_charges_are_nonzero():
    b = PaperBroker(100_000.0)
    charge = b.costs.charges(Side.SELL, 100, 500.0)
    assert charge > 0
