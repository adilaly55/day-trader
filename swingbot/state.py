"""Bot memory between runs (JSON) and a permanent trade journal (SQLite), both in ~/.swingbot/."""
from __future__ import annotations

import copy
import json
import sqlite3
from datetime import datetime
from pathlib import Path

DEFAULT = {"positions": {}, "pending": None, "done": {}, "paused": False, "tickers": {}, "tickers_date": None}


class State:
    def __init__(self, home: Path):
        home.mkdir(parents=True, exist_ok=True)
        self.path = home / "state.json"
        self.data = {**copy.deepcopy(DEFAULT), **(json.loads(self.path.read_text()) if self.path.exists() else {})}
        self.db = sqlite3.connect(home / "journal.sqlite")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS trades (symbol TEXT, ticker TEXT, quantity REAL, entry_date TEXT,
                entry_price REAL, exit_date TEXT, exit_price REAL, pnl REAL, ret_pct REAL, days INTEGER,
                reason TEXT, broker TEXT);
            CREATE TABLE IF NOT EXISTS events (ts TEXT, kind TEXT, message TEXT);
        """)

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=1, default=str))
        tmp.replace(self.path)                       # atomic: never leaves a half-written file

    @property
    def positions(self) -> dict:
        return self.data["positions"]

    def log(self, kind: str, message: str) -> None:
        self.db.execute("INSERT INTO events VALUES (?,?,?)", (datetime.now().isoformat(timespec="seconds"), kind, message))
        self.db.commit()

    def record_trade(self, symbol: str, pos: dict, exit_date: str, exit_price: float, days: int, reason: str,
                     broker: str) -> dict:
        pnl = (exit_price - pos["entry_price"]) * pos["quantity"]
        ret = (exit_price / pos["entry_price"] - 1) * 100
        self.db.execute("INSERT INTO trades VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
            symbol, pos["ticker"], pos["quantity"], pos["entry_date"], pos["entry_price"], exit_date, exit_price,
            round(pnl, 4), round(ret, 3), days, reason, broker))
        self.db.commit()
        return {"pnl": pnl, "ret": ret}

    def trades(self) -> list[tuple]:
        return self.db.execute("SELECT symbol, entry_date, exit_date, entry_price, exit_price, pnl, ret_pct, days, "
                               "reason FROM trades ORDER BY exit_date").fetchall()
