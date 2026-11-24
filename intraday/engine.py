"""The trading loop. Feed it bars (all symbols for one timestamp at a time); it manages
stops/targets, asks the strategy for entries, enforces risk limits and flattens before the close.
The same engine runs backtests and live/paper trading - only the data feed and broker change."""
from __future__ import annotations

from datetime import datetime
from typing import Callable
from zoneinfo import ZoneInfo

from .broker import Broker
from .config import Config
from .models import Bar, Position
from .risk import RiskManager
from .strategy import OpeningRangeBreakout
from .tracker import Tracker


class Engine:
    def __init__(self, cfg: Config, broker: Broker, tracker: Tracker,
                 strategy=None, risk: RiskManager | None = None,
                 log: Callable[[str], None] | None = print):
        self.cfg = cfg
        self.broker = broker
        self.tracker = tracker
        self.strategy = strategy or OpeningRangeBreakout(cfg)
        self.risk = risk or RiskManager(cfg)
        self.log = log or (lambda _msg: None)
        self.tz = ZoneInfo(cfg.timezone)
        self.marks: dict[str, float] = {}
        self.day = None
        self.last_ts: datetime | None = None

    # ---- public -------------------------------------------------------------
    def warmup(self, bars: list[Bar]) -> None:
        """Update indicators/marks without trading (used when starting live mid-session)."""
        if not bars:
            return
        now = bars[0].ts.astimezone(self.tz)
        if not self._in_session(now):
            return
        if now.date() != self.day:
            self._start_day(now)
        for bar in bars:
            self.marks[bar.symbol] = bar.close
            self.strategy.on_bar(bar, now)

    def process_bars(self, bars: list[Bar]) -> None:
        if not bars:
            return
        now = bars[0].ts.astimezone(self.tz)
        if not self._in_session(now):
            return
        if now.date() != self.day:
            if self.tracker.positions and self.last_ts:      # data ended early yesterday: never hold overnight
                self.flatten_all(self.last_ts, "session_end")
            self._start_day(now)
        self.last_ts = now

        # 1) manage open positions against this bar's range
        for bar in bars:
            self.marks[bar.symbol] = bar.close
            self._manage(bar, now)

        # 2) new entries
        past_flatten = now.time() >= self.cfg.flatten_at
        for bar in bars:
            sig = self.strategy.on_bar(bar, now)
            if (sig and not past_flatten and bar.symbol not in self.tracker.positions
                    and self.risk.can_open(len(self.tracker.positions))):
                self._enter(bar, sig, now)

        # 3) risk + end of day
        if self.risk.check_daily_loss(self.tracker.equity(self.marks)) and self.tracker.positions:
            self.flatten_all(now, "daily_loss_limit")
        if past_flatten and self.tracker.positions:
            self.flatten_all(now, "eod_flatten")

    def flatten_all(self, now: datetime, reason: str) -> None:
        for pos in list(self.tracker.positions.values()):
            self._exit(pos, self.marks.get(pos.symbol, pos.entry_price), now, reason)

    def finish(self) -> None:
        if self.tracker.positions and self.last_ts:
            self.flatten_all(self.last_ts, "end_of_data")

    # ---- internals ----------------------------------------------------------
    def _in_session(self, now: datetime) -> bool:
        return self.cfg.market_open <= now.time() < self.cfg.market_close

    def _start_day(self, now: datetime) -> None:
        self.day = now.date()
        self.risk.new_day(self.tracker.equity(self.marks))

    def _enter(self, bar: Bar, sig, now: datetime) -> None:
        equity = self.tracker.equity(self.marks)
        qty = self.risk.size(equity, bar.close, sig.stop)
        if qty <= 0:
            return
        fill = self.broker.market_order(bar.symbol, "buy" if sig.side == "long" else "sell", qty, bar.close, now)
        direction = 1 if sig.side == "long" else -1
        risk_per_share = abs(fill.price - sig.stop)
        target = fill.price + direction * self.cfg.reward_risk * risk_per_share
        pos = self.tracker.open_position(bar.symbol, sig.side, fill, now, sig.stop, target)
        self.strategy.record_entry(bar.symbol)
        self.log(f"{now:%Y-%m-%d %H:%M} OPEN  {pos.side.upper():5} {pos.qty:>5} {pos.symbol:<5} @ {pos.entry_price:.2f}"
                 f"  stop {pos.stop:.2f}  target {pos.target:.2f}  ({sig.reason})")

    def _manage(self, bar: Bar, now: datetime) -> None:
        pos = self.tracker.positions.get(bar.symbol)
        if not pos:
            return
        exit_price = reason = None
        if pos.side == "long":
            if bar.open <= pos.stop:
                exit_price, reason = bar.open, "stop"          # gapped through the stop
            elif bar.low <= pos.stop:
                exit_price, reason = pos.stop, "stop"          # stop checked first = conservative
            elif bar.open >= pos.target:
                exit_price, reason = bar.open, "target"
            elif bar.high >= pos.target:
                exit_price, reason = pos.target, "target"
        else:
            if bar.open >= pos.stop:
                exit_price, reason = bar.open, "stop"
            elif bar.high >= pos.stop:
                exit_price, reason = pos.stop, "stop"
            elif bar.open <= pos.target:
                exit_price, reason = bar.open, "target"
            elif bar.low <= pos.target:
                exit_price, reason = pos.target, "target"
        if exit_price is not None:
            self._exit(pos, exit_price, now, reason)

    def _exit(self, pos: Position, ref_price: float, now: datetime, reason: str) -> None:
        fill = self.broker.market_order(pos.symbol, "sell" if pos.side == "long" else "buy", pos.qty, ref_price, now)
        t = self.tracker.close_position(pos.symbol, fill, now, reason)
        self.log(f"{now:%Y-%m-%d %H:%M} CLOSE {t.side.upper():5} {t.qty:>5} {t.symbol:<5} @ {t.exit_price:.2f}"
                 f"  P&L {t.pnl:+,.2f} ({t.r_multiple:+.2f}R)  [{reason}]")
