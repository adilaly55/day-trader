from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Bar:
    """One OHLCV bar. `ts` is the bar's START time and must be timezone-aware."""
    symbol: str
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Fill:
    price: float
    qty: int
    commission: float = 0.0


@dataclass
class Position:
    symbol: str
    side: str                 # "long" | "short"
    qty: int
    entry_price: float
    entry_time: datetime
    stop: float
    target: float
    entry_commission: float = 0.0

    @property
    def direction(self) -> int:
        return 1 if self.side == "long" else -1

    def unrealized(self, price: float) -> float:
        return self.direction * (price - self.entry_price) * self.qty

    @property
    def initial_risk(self) -> float:
        return abs(self.entry_price - self.stop) * self.qty


@dataclass
class Trade:
    symbol: str
    side: str
    qty: int
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    pnl: float                # net of commissions
    r_multiple: float         # pnl / initial risk
    exit_reason: str
