"""Tracks open positions, closed trades and P&L, and journals every trade to SQLite."""
from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import datetime

from .models import Fill, Position, Trade

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, mode TEXT, started TEXT, starting_equity REAL);
CREATE TABLE IF NOT EXISTS trades (
    run_id TEXT, symbol TEXT, side TEXT, qty INTEGER, entry_price REAL, exit_price REAL,
    entry_time TEXT, exit_time TEXT, pnl REAL, r_multiple REAL, exit_reason TEXT
);
"""


class Tracker:
    def __init__(self, starting_equity: float, journal_path: str | None = None, mode: str = "backtest"):
        self.starting_equity = starting_equity
        self.realized = 0.0
        self.positions: dict[str, Position] = {}
        self.trades: list[Trade] = []
        self.run_id = f"{mode}-{datetime.now():%Y%m%d-%H%M%S}"
        self.db = None
        if journal_path:
            self.db = sqlite3.connect(journal_path)
            self.db.executescript(_SCHEMA)
            self.db.execute("INSERT OR REPLACE INTO runs VALUES (?,?,?,?)",
                            (self.run_id, mode, datetime.now().isoformat(timespec="seconds"), starting_equity))
            self.db.commit()

    def open_position(self, symbol: str, side: str, fill: Fill, ts: datetime, stop: float, target: float) -> Position:
        if symbol in self.positions:
            raise ValueError(f"Already have a position in {symbol}")
        pos = Position(symbol, side, fill.qty, fill.price, ts, stop, target, fill.commission)
        self.positions[symbol] = pos
        self.realized -= fill.commission
        return pos

    def close_position(self, symbol: str, fill: Fill, ts: datetime, reason: str) -> Trade:
        pos = self.positions.pop(symbol)
        gross = pos.direction * (fill.price - pos.entry_price) * pos.qty
        self.realized += gross - fill.commission
        pnl = gross - pos.entry_commission - fill.commission
        risk = pos.initial_risk
        trade = Trade(symbol, pos.side, pos.qty, pos.entry_price, fill.price, pos.entry_time, ts,
                      round(pnl, 2), round(pnl / risk, 2) if risk else 0.0, reason)
        self.trades.append(trade)
        if self.db:
            self.db.execute("INSERT INTO trades VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
                self.run_id, trade.symbol, trade.side, trade.qty, trade.entry_price, trade.exit_price,
                trade.entry_time.isoformat(), trade.exit_time.isoformat(), trade.pnl, trade.r_multiple,
                trade.exit_reason))
            self.db.commit()
        return trade

    def unrealized(self, marks: dict[str, float]) -> float:
        return sum(p.unrealized(marks.get(s, p.entry_price)) for s, p in self.positions.items())

    def equity(self, marks: dict[str, float]) -> float:
        return self.starting_equity + self.realized + self.unrealized(marks)


def summarize(trades: list[Trade], starting_equity: float) -> dict:
    trades = sorted(trades, key=lambda t: t.exit_time)
    wins = [t.pnl for t in trades if t.pnl > 0]
    losses = [t.pnl for t in trades if t.pnl < 0]
    gross_profit, gross_loss = sum(wins), -sum(losses)
    equity = peak = starting_equity
    max_dd = 0.0
    daily: dict = defaultdict(float)
    for t in trades:
        equity += t.pnl
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak)
        daily[t.exit_time.date()] += t.pnl
    n = len(trades)
    return {
        "trades": n,
        "win_rate": len(wins) / n if n else 0.0,
        "net_pnl": sum(t.pnl for t in trades),
        "return_pct": (equity - starting_equity) / starting_equity,
        "profit_factor": (gross_profit / gross_loss) if gross_loss else float("inf") if gross_profit else 0.0,
        "avg_r": sum(t.r_multiple for t in trades) / n if n else 0.0,
        "avg_win": gross_profit / len(wins) if wins else 0.0,
        "avg_loss": -gross_loss / len(losses) if losses else 0.0,
        "max_drawdown_pct": max_dd,
        "days_traded": len(daily),
        "green_days": sum(1 for v in daily.values() if v > 0),
        "best_day": max(daily.values(), default=0.0),
        "worst_day": min(daily.values(), default=0.0),
        "exit_reasons": dict(sorted(_count(t.exit_reason for t in trades).items())),
    }


def _count(items) -> dict:
    out: dict = defaultdict(int)
    for i in items:
        out[i] += 1
    return out


def format_summary(s: dict) -> str:
    return "\n".join([
        "-" * 44,
        f"Trades           {s['trades']}   (days traded: {s['days_traded']}, green: {s['green_days']})",
        f"Win rate         {s['win_rate']:.1%}",
        f"Net P&L          ${s['net_pnl']:,.2f}   ({s['return_pct']:+.2%})",
        f"Profit factor    {s['profit_factor']:.2f}",
        f"Avg R / trade    {s['avg_r']:+.2f}",
        f"Avg win / loss   ${s['avg_win']:,.2f} / ${s['avg_loss']:,.2f}",
        f"Max drawdown     {s['max_drawdown_pct']:.2%}",
        f"Best / worst day ${s['best_day']:,.2f} / ${s['worst_day']:,.2f}",
        f"Exit reasons     {s['exit_reasons']}",
        "-" * 44,
    ])
