"""Transaction cost model for Indian intraday equity/derivatives.

Charges are applied per fill. This matters a lot for an intraday, high-frequency
strategy: costs are frequently the difference between a profitable backtest and a
losing live account, so they are modelled explicitly rather than ignored.
"""

from __future__ import annotations

from tradingbot.config import CostConfig
from tradingbot.core.events import Side


class CostModel:
    def __init__(self, cfg: CostConfig):
        self.cfg = cfg

    def charges(self, side: Side, qty: int, price: float) -> float:
        """Total statutory + broker charges for one fill (excludes slippage)."""
        c = self.cfg
        turnover = qty * price

        brokerage = min(c.brokerage_cap, turnover * c.brokerage_pct)
        stt = turnover * c.stt_sell_pct if side is Side.SELL else 0.0
        stamp = turnover * c.stamp_buy_pct if side is Side.BUY else 0.0
        exch = turnover * c.exchange_txn_pct
        sebi = turnover * c.sebi_pct
        gst = c.gst_pct * (brokerage + exch + sebi)

        return round(brokerage + stt + stamp + exch + sebi + gst, 4)

    def slippage_price(self, side: Side, price: float) -> float:
        """Adverse fill price: buys fill a touch higher, sells a touch lower."""
        return price * (1 + side.sign * self.cfg.slippage_pct)
