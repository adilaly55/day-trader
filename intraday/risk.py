from __future__ import annotations

import math

from .config import Config


class RiskManager:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.day_start_equity = cfg.starting_equity
        self.halted = False

    def new_day(self, equity: float) -> None:
        self.day_start_equity = equity
        self.halted = False

    def check_daily_loss(self, equity: float) -> bool:
        """Returns True if trading is halted for the rest of the day."""
        if equity <= self.day_start_equity * (1 - self.cfg.daily_loss_limit_pct):
            self.halted = True
        return self.halted

    def can_open(self, open_positions: int) -> bool:
        return not self.halted and open_positions < self.cfg.max_open_positions

    def size(self, equity: float, entry: float, stop: float) -> int:
        """Shares such that hitting the stop loses risk_per_trade_pct of equity, capped by max_position_pct."""
        per_share_risk = abs(entry - stop)
        if per_share_risk <= 0 or entry <= 0:
            return 0
        by_risk = equity * self.cfg.risk_per_trade_pct / per_share_risk
        by_notional = equity * self.cfg.max_position_pct / entry
        return max(0, math.floor(min(by_risk, by_notional)))
