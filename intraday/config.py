"""All tunable settings in one place. Override any field with a JSON file (see config.example.json)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from datetime import time

_TIME_FIELDS = {"market_open", "market_close", "no_new_entries_after", "flatten_at"}


@dataclass
class Config:
    symbols: list[str] = field(default_factory=lambda: ["AAPL", "MSFT", "NVDA", "AMD", "TSLA"])
    starting_equity: float = 100_000.0

    # Session (exchange local time)
    timezone: str = "America/New_York"
    market_open: time = time(9, 30)
    market_close: time = time(16, 0)
    no_new_entries_after: time = time(15, 0)
    flatten_at: time = time(15, 55)          # everything is closed at/after this bar -> no overnight risk

    # Strategy: opening-range breakout confirmed by VWAP
    opening_range_minutes: int = 15
    reward_risk: float = 2.0                  # target = entry +/- reward_risk * (entry - stop)
    max_trades_per_symbol_per_day: int = 1
    min_range_pct: float = 0.002              # skip days where the opening range is too tight...
    max_range_pct: float = 0.03               # ...or too wide
    max_extension: float = 0.5                # don't chase: close must be within 0.5x range of the breakout level

    # Risk
    risk_per_trade_pct: float = 0.005         # lose at most 0.5% of equity if the stop is hit
    max_position_pct: float = 0.20            # no single position larger than 20% of equity
    max_open_positions: int = 3
    daily_loss_limit_pct: float = 0.02        # down 2% on the day -> flatten and stop trading until tomorrow

    # Simulated execution costs (paper broker / backtests)
    slippage_bps: float = 2.0
    commission_per_share: float = 0.0

    journal_path: str = "journal.sqlite"

    @classmethod
    def load(cls, path: str | None) -> "Config":
        cfg = cls()
        if not path:
            return cfg
        with open(path) as f:
            data = json.load(f)
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"Unknown config keys: {sorted(unknown)}")
        for key, value in data.items():
            if key in _TIME_FIELDS:
                value = time.fromisoformat(value)
            setattr(cfg, key, value)
        return cfg
