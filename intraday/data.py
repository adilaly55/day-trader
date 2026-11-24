"""Bar sources for backtesting. Each yields lists of bars that share a timestamp, in time order."""
from __future__ import annotations

import csv
import math
import random
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Iterator
from zoneinfo import ZoneInfo

from .config import Config
from .models import Bar


def group_by_ts(bars: list[Bar]) -> Iterator[list[Bar]]:
    groups: dict[datetime, list[Bar]] = defaultdict(list)
    for b in bars:
        groups[b.ts].append(b)
    for ts in sorted(groups):
        yield groups[ts]


def csv_bars(path: str, cfg: Config) -> Iterator[list[Bar]]:
    """CSV with columns: timestamp,symbol,open,high,low,close,volume (timestamp = bar start, ISO 8601).
    Naive timestamps are interpreted in cfg.timezone."""
    tz = ZoneInfo(cfg.timezone)
    bars = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            ts = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=tz)
            bars.append(Bar(row["symbol"], ts, float(row["open"]), float(row["high"]),
                            float(row["low"]), float(row["close"]), float(row["volume"])))
    return group_by_ts(bars)


def synthetic_bars(symbols: list[str], days: int, seed: int, cfg: Config,
                   start: date = date(2026, 1, 5)) -> Iterator[list[Bar]]:
    """Random-walk 1-minute bars for testing the plumbing. NOT a measure of strategy edge."""
    rng = random.Random(seed)
    tz = ZoneInfo(cfg.timezone)
    prices = {s: rng.uniform(40, 400) for s in symbols}
    d, produced = start, 0
    while produced < days:
        if d.weekday() < 5:
            produced += 1
            drift = {s: rng.gauss(0, 0.012) / 390 for s in symbols}     # some days trend, some chop
            for s in symbols:
                prices[s] *= math.exp(rng.gauss(0, 0.008))               # overnight gap
            session_start = datetime.combine(d, cfg.market_open, tz)
            for m in range(390):
                ts = session_start + timedelta(minutes=m)
                vol = 0.0008 * (2.0 if m < 30 else 1.3 if m > 360 else 1.0)
                group = []
                for s in symbols:
                    o = prices[s]
                    c = o * math.exp(drift[s] + rng.gauss(0, vol))
                    h = max(o, c) * (1 + abs(rng.gauss(0, vol / 2)))
                    l = min(o, c) * (1 - abs(rng.gauss(0, vol / 2)))
                    v = rng.randint(5_000, 50_000) * (3 if m < 30 or m > 360 else 1)
                    group.append(Bar(s, ts, round(o, 2), round(h, 2), round(l, 2), round(c, 2), v))
                    prices[s] = c
                yield group
        d += timedelta(days=1)
