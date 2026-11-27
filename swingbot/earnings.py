"""Upcoming earnings dates from Finnhub, so the bot never holds a stock through its earnings report."""
from __future__ import annotations

from datetime import date, timedelta

from .http import Client


class Earnings:
    def __init__(self, token: str):
        self.http = Client("https://finnhub.io/api/v1", {"X-Finnhub-Token": token or "x"})

    def reporting_within(self, days: int, today: date | None = None) -> set[str]:
        today = today or date.today()
        resp = self.http.request("GET", "/calendar/earnings",
                                 {"from": today.isoformat(), "to": (today + timedelta(days=days)).isoformat()})
        return {row["symbol"] for row in (resp or {}).get("earningsCalendar", []) if row.get("symbol")}
