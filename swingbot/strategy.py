"""The trading rules, as pure functions (no network), so they are easy to test.

ENTRY  (decided ~15 min before the US close, bought at the next open):
       price > SMA(200)  and  RSI(2) < 20  and  20-day avg traded value > $20M
       and no earnings report within the next ~8 calendar days.  Lowest RSI first.
EXIT   (decided ~15 min before the close, sold right away):
       price > SMA(5)  or  held for 5 trading days.   Plus a 12% stop order held at the broker.
'price' is the live price at decision time; history is completed daily closes.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import Config
from .indicators import rsi, sma


@dataclass
class Candidate:
    symbol: str
    price: float
    rsi: float
    sma_trend: float


def entry_signal(cfg: Config, symbol: str, history: list[dict], price: float) -> Candidate | None:
    closes = [r["close"] for r in history] + [price]
    if len(closes) < cfg.trend_sma + 1:
        return None
    trend = sma(closes, cfg.trend_sma)
    r = rsi(closes[-60:], cfg.rsi_period)
    vols = history[-20:]
    dollar_vol = sum(b["close"] * b["volume"] for b in vols) / max(len(vols), 1)
    if trend is None or r is None or dollar_vol < cfg.min_dollar_volume:
        return None
    if price > trend and r < cfg.rsi_max:
        return Candidate(symbol, price, round(r, 2), round(trend, 2))
    return None


def exit_reason(cfg: Config, history: list[dict], price: float, days_held: int) -> str | None:
    closes = [r["close"] for r in history] + [price]
    s = sma(closes, cfg.exit_sma)
    if s is not None and price > s:
        return f"recovered (price {price:.2f} > {cfg.exit_sma}-day avg {s:.2f})"
    if days_held >= cfg.max_hold_days:
        return f"time limit ({days_held} trading days)"
    return None


def rank(cands: list[Candidate]) -> list[Candidate]:
    return sorted(cands, key=lambda c: c.rsi)
