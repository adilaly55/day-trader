"""US market calendar fallback (the bot prefers Trading 212's live exchange schedule)."""
from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")

HOLIDAYS = {
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19", "2026-07-03",
    "2026-09-07", "2026-11-26", "2026-12-25",
    "2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31", "2027-06-18", "2027-07-05",
    "2027-09-06", "2027-11-25", "2027-12-24",
}
EARLY_CLOSE = {"2026-11-27", "2026-12-24", "2027-11-26"}     # 13:00 ET


def session(day: date) -> tuple[datetime, datetime] | None:
    if day.weekday() >= 5 or day.isoformat() in HOLIDAYS:
        return None
    close = time(13, 0) if day.isoformat() in EARLY_CLOSE else time(16, 0)
    return datetime.combine(day, time(9, 30), NY), datetime.combine(day, close, NY)
