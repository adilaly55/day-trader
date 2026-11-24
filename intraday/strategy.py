"""Opening Range Breakout (ORB) with a VWAP filter.

1. Record the high/low of the first `opening_range_minutes` of the session.
2. Go LONG when a bar closes above the range high AND above VWAP.
   Go SHORT when a bar closes below the range low AND below VWAP.
3. Stop = midpoint of the opening range. Target = reward_risk x the risk.
4. Skip days where the range is too tight/wide and don't chase extended moves.

Swap in your own strategy by writing a class with the same `on_bar` / `record_entry` methods.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .config import Config
from .models import Bar


@dataclass
class Signal:
    side: str       # "long" | "short"
    stop: float
    reason: str


class _DayState:
    def __init__(self, day: date):
        self.day = day
        self.or_high = float("-inf")
        self.or_low = float("inf")
        self.pv = 0.0
        self.vol = 0.0
        self.trades = 0


class OpeningRangeBreakout:
    name = "orb_vwap"

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.states: dict[str, _DayState] = {}
        self.or_end = (datetime.combine(date(2000, 1, 1), cfg.market_open)
                       + timedelta(minutes=cfg.opening_range_minutes)).time()

    def on_bar(self, bar: Bar, now: datetime) -> Signal | None:
        """Called for every bar (also while a position is open) so indicators stay current."""
        cfg = self.cfg
        st = self.states.get(bar.symbol)
        if st is None or st.day != now.date():
            st = self.states[bar.symbol] = _DayState(now.date())

        typical = (bar.high + bar.low + bar.close) / 3
        st.pv += typical * bar.volume
        st.vol += bar.volume
        vwap = st.pv / st.vol if st.vol > 0 else bar.close

        t = now.time()
        if t < self.or_end:
            st.or_high = max(st.or_high, bar.high)
            st.or_low = min(st.or_low, bar.low)
            return None
        if st.or_high == float("-inf"):           # never saw the opening range (e.g. started mid-day)
            return None
        if st.trades >= cfg.max_trades_per_symbol_per_day or t >= cfg.no_new_entries_after:
            return None

        rng = st.or_high - st.or_low
        mid = (st.or_high + st.or_low) / 2
        if not (cfg.min_range_pct <= rng / mid <= cfg.max_range_pct):
            return None
        max_ext = cfg.max_extension * rng

        if bar.close > st.or_high and bar.close > vwap and bar.close - st.or_high <= max_ext:
            return Signal("long", stop=mid, reason=f"close {bar.close:.2f} > OR high {st.or_high:.2f}, VWAP {vwap:.2f}")
        if bar.close < st.or_low and bar.close < vwap and st.or_low - bar.close <= max_ext:
            return Signal("short", stop=mid, reason=f"close {bar.close:.2f} < OR low {st.or_low:.2f}, VWAP {vwap:.2f}")
        return None

    def record_entry(self, symbol: str) -> None:
        self.states[symbol].trades += 1
