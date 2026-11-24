from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from .models import Fill


class Broker(ABC):
    @abstractmethod
    def market_order(self, symbol: str, side: str, qty: int, ref_price: float, ts: datetime) -> Fill:
        """side is "buy" or "sell". ref_price is the price the engine expects (used for simulation)."""


class PaperBroker(Broker):
    """Simulated fills at the reference price, worsened by slippage, plus per-share commission."""

    def __init__(self, slippage_bps: float = 2.0, commission_per_share: float = 0.0):
        self.slippage_bps = slippage_bps
        self.commission_per_share = commission_per_share

    def market_order(self, symbol, side, qty, ref_price, ts):
        slip = ref_price * self.slippage_bps / 10_000
        price = ref_price + slip if side == "buy" else ref_price - slip
        return Fill(round(price, 4), qty, qty * self.commission_per_share)
