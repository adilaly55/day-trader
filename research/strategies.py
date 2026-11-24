"""Long-only intraday strategy candidates. Each returns a DataFrame of trades (see lab.trade_row)
with a 'rank' column used by the daily scanner (lower rank = higher priority).

All of them exit by 12:30 ET at the latest (end of the 18:30-21:30 Dubai window).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import NBARS, Sym, trade_row

LAST_ENTRY_BAR = 23        # no new entries after 11:30 ET (bar starting 11:25 closes 11:30)


def _eligible(s: Sym, d: int, min_price=5.0, min_atr=0.5, min_avg_vol=1e6) -> bool:
    f = s.feat.iloc[d]
    return (f.prev_close > min_price and f.atr14 > min_atr and f.avg_vol20 > min_avg_vol
            and np.isfinite(f.rvol5) and np.isfinite(f.gap))


def regime_ok(market: Sym | None, date) -> bool:
    """Market filter: SPY's previous close above its 20-day average (uptrend)."""
    if market is None:
        return True
    try:
        f = market.feat.loc[pd.Timestamp(date)]
    except KeyError:
        return False
    return bool(f.prev_close > f.sma20)


def _run(syms, market, use_regime, fn) -> pd.DataFrame:
    rows = []
    for s in syms.values():
        if s.name in ("SPY",):
            continue
        for d in range(len(s.dates)):
            if not _eligible(s, d):
                continue
            if use_regime and not regime_ok(market, s.dates[d]):
                continue
            r = fn(s, d)
            if r:
                rows.append(r)
    return pd.DataFrame(rows)


# 1) Opening-range breakout on "stocks in play" ----------------------------------------
def orb_in_play(syms, market=None, use_regime=False, or_bars=1, min_rvol=1.5, stop_atr=0.2,
                target_r=None, vwap_filter=False):
    def fn(s: Sym, d: int):
        f = s.feat.iloc[d]
        if f.rvol5 < min_rvol:
            return None
        orh, orl = s.H[d, :or_bars].max(), s.L[d, :or_bars].min()
        if s.C[d, or_bars - 1] <= s.O[d, 0]:             # opening range must close green
            return None
        for b in range(or_bars, LAST_ENTRY_BAR + 1):
            if s.C[d, b] > orh and (not vwap_filter or s.C[d, b] > s.VWAP[d, b]):
                entry = s.C[d, b]
                stop = entry - stop_atr * f.atr14
                target = entry + target_r * (entry - stop) if target_r else None
                return trade_row(s, d, b, stop, target, rank=-f.rvol5)
        return None
    return _run(syms, market, use_regime, fn)


# 2) Gap-and-go -------------------------------------------------------------------------
def gap_and_go(syms, market=None, use_regime=False, min_gap=0.02, min_rvol=2.0, target_r=None):
    def fn(s: Sym, d: int):
        f = s.feat.iloc[d]
        if f.gap < min_gap or f.rvol5 < min_rvol or s.C[d, 0] <= s.O[d, 0]:
            return None
        stop = s.L[d, 0]
        entry = s.C[d, 0]
        if entry - stop <= 0:
            return None
        target = entry + target_r * (entry - stop) if target_r else None
        return trade_row(s, d, 0, stop, target, rank=-f.rvol5)
    return _run(syms, market, use_regime, fn)


# 3) Gap-down reversal in an uptrending stock --------------------------------------------
def gap_down_reversal(syms, market=None, use_regime=False, max_gap=-0.02, fill_target=True):
    def fn(s: Sym, d: int):
        f = s.feat.iloc[d]
        if f.gap > max_gap or not (f.prev_close > f.sma50):
            return None
        for b in range(1, LAST_ENTRY_BAR + 1):
            if s.C[d, b] > s.H[d, 0] and s.C[d, b] > s.VWAP[d, b]:
                stop = s.L[d, :b + 1].min()
                entry = s.C[d, b]
                if entry - stop <= 0:
                    return None
                target = f.prev_close if fill_target and f.prev_close > entry else None
                return trade_row(s, d, b, stop, target, rank=f.gap)       # bigger gap first
        return None
    return _run(syms, market, use_regime, fn)


# 4) VWAP pullback in a strong morning trend ----------------------------------------------
def vwap_pullback(syms, market=None, use_regime=False, min_move=0.01, min_rvol=1.5, target_r=2.0):
    def fn(s: Sym, d: int):
        f = s.feat.iloc[d]
        if f.rvol5 < min_rvol:
            return None
        if s.C[d, 5] / s.O[d, 0] - 1 < min_move or s.C[d, 5] <= s.VWAP[d, 5]:
            return None                                   # must be up >= min_move at 10:00, above VWAP
        for b in range(6, LAST_ENTRY_BAR + 1):
            vw = s.VWAP[d, b - 1]
            if s.L[d, b] <= vw * 1.001 and s.C[d, b] > vw and s.C[d, b] > s.O[d, b]:
                entry = s.C[d, b]
                stop = min(s.L[d, b], vw) - 0.1 * f.atr14
                target = entry + target_r * (entry - stop) if target_r else None
                return trade_row(s, d, b, stop, target, rank=-f.rvol5)
            if s.C[d, b] < s.VWAP[d, b] * 0.995:          # trend broken, give up for the day
                return None
        return None
    return _run(syms, market, use_regime, fn)


# Baselines -------------------------------------------------------------------------------
def random_entries(syms, market=None, use_regime=False, stop_atr=0.5, p=0.03, seed=0):
    """Random entries on eligible stocks: what 'no edge' looks like with the same exits/costs."""
    rng = np.random.default_rng(seed)

    def fn(s: Sym, d: int):
        if rng.random() > p:
            return None
        b = int(rng.integers(0, LAST_ENTRY_BAR + 1))
        entry = s.C[d, b]
        return trade_row(s, d, b, entry - stop_atr * s.feat.iloc[d].atr14, None, rank=rng.random())
    return _run(syms, market, use_regime, fn)


def spy_morning(syms, market=None, use_regime=False):
    s = syms["SPY"]
    rows = []
    for d in range(len(s.dates)):
        if use_regime and not regime_ok(market, s.dates[d]):
            continue
        rows.append(trade_row(s, d, 0, -1e9, None, rank=0))
    return pd.DataFrame(rows)
