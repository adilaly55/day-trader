"""Indicators on plain lists of floats (oldest first). Match research/swing.py (pandas) exactly."""
from __future__ import annotations


def sma(values: list[float], n: int) -> float | None:
    if len(values) < n:
        return None
    return sum(values[-n:]) / n


def rsi(values: list[float], n: int) -> float | None:
    """Wilder-style RSI using an EWM with alpha=1/n, adjust=False (same as pandas ewm in research)."""
    if len(values) < n + 1:
        return None
    up = dn = None
    for prev, cur in zip(values[:-1], values[1:]):
        d = cur - prev
        u, w = max(d, 0.0), max(-d, 0.0)
        if up is None:
            up, dn = u, w
        else:
            up += (u - up) / n
            dn += (w - dn) / n
    if dn == 0:
        return 100.0 if up > 0 else 50.0
    return 100 - 100 / (1 + up / dn)
