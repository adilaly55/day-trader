"""Multi-day (1-5 day) long-only strategy research on daily bars since 2016.

Execution model
  * Signals use only data up to the signal day's close.
  * Entry at the signal day's CLOSE (the bot runs ~15 minutes before the US close,
    00:45 Dubai in winter) or, optionally, the next day's OPEN.
  * Stop-loss checked against each later day's low (gap through -> exit at the open).
  * Profit exits are evaluated at the close; a time exit after `max_hold` days.
  * Costs: COST_BPS per side. No overnight fees (Trading 212 Invest = real shares).

Portfolio: `SLOTS` equal slots; a signal is taken only if a slot is free on its
entry day (best-ranked first). Daily mark-to-market for drawdown/Sharpe.

Split: tune on 2016-2021, judge on 2022-2026 (includes the 2022 bear market).

Survivorship caveat: the stock list is today's survivors, which flatters dip-buying.
ETFs have no such bias, so every strategy is also reported on ETFs alone.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from universe import ETFS

DATA = Path(__file__).resolve().parent.parent / "data" / "daily_long"
COST_BPS = 5.0
SLOTS = 5
EXIT_NEXT_OPEN = False      # True: exit signals seen at the close are executed at the next open (no close peeking)
IS_END = pd.Timestamp("2021-12-31")


@dataclass
class D:
    name: str
    dates: np.ndarray
    O: np.ndarray
    H: np.ndarray
    L: np.ndarray
    C: np.ndarray
    V: np.ndarray
    ind: dict


def _rsi(c: pd.Series, n: int) -> pd.Series:
    diff = c.diff()
    up = diff.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-diff.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def load() -> dict[str, D]:
    out = {}
    for fp in sorted(DATA.glob("*.parquet")):
        df = pd.read_parquet(fp).sort_values("date").reset_index(drop=True)
        c, h, l = df["close"], df["high"], df["low"]
        pc = c.shift(1)
        tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
        ind = {
            "sma5": c.rolling(5).mean(), "sma10": c.rolling(10).mean(), "sma50": c.rolling(50).mean(),
            "sma200": c.rolling(200).mean(), "rsi2": _rsi(c, 2), "rsi3": _rsi(c, 3),
            "atr14": tr.rolling(14).mean(), "ibs": (c - l) / (h - l).replace(0, np.nan),
            "low5": c.rolling(5).min(), "low10": c.rolling(10).min(), "high20": c.rolling(20).max(),
            "vol20": df["volume"].rolling(20).mean(), "ret1": c.pct_change(),
            "gap": df["open"] / pc - 1, "dollar_vol": (c * df["volume"]).rolling(20).mean(),
        }
        out[fp.stem] = D(fp.stem, df["date"].values.astype("datetime64[D]"), df["open"].values,
                         h.values, l.values, c.values, df["volume"].values.astype(float),
                         {k: v.to_numpy(dtype=float) for k, v in ind.items()})
    return out


# ------------------------------------------------------------------------- trade walking
def walk(s: D, i: int, max_hold: int, stop: float | None, exit_fn, next_open: bool) -> dict | None:
    """Enter after signal day i. Returns trade dict with daily mark-to-market path."""
    n = len(s.C)
    if next_open:
        if i + 1 >= n:
            return None
        e_idx, entry = i + 1, s.O[i + 1]
    else:
        e_idx, entry = i, s.C[i]
    path = []                                  # (date_index, price at that day's close or exit)
    j = e_idx
    first = e_idx + (0 if next_open else 1)
    for j in range(first, min(n, e_idx + max_hold + 1)):
        if stop is not None:
            if s.O[j] <= stop:
                path.append((j, s.O[j])); return _done(s, i, e_idx, entry, path, "stop")
            if s.L[j] <= stop:
                path.append((j, stop)); return _done(s, i, e_idx, entry, path, "stop")
        path.append((j, s.C[j]))
        if exit_fn(s, j, entry):
            if EXIT_NEXT_OPEN and j + 1 < n:
                path.append((j + 1, s.O[j + 1]))
            return _done(s, i, e_idx, entry, path, "exit")
    if not path:
        return None
    return _done(s, i, e_idx, entry, path, "time")


def _done(s, i, e_idx, entry, path, reason):
    cost = COST_BPS / 10_000
    exit_price = path[-1][1]
    return {"symbol": s.name, "signal_i": i, "entry_date": pd.Timestamp(s.dates[e_idx]),
            "exit_date": pd.Timestamp(s.dates[path[-1][0]]), "entry": entry, "exit": exit_price,
            "days": path[-1][0] - e_idx, "reason": reason,
            "ret": exit_price / entry - 1 - 2 * cost,
            "path": [(pd.Timestamp(s.dates[j]), p) for j, p in path]}


# ------------------------------------------------------------------------- portfolio
def portfolio(trades: list[dict], slots: int = SLOTS) -> tuple[pd.DataFrame, pd.Series]:
    """Take trades in entry-date order (best rank first) while slots are free; daily MTM returns."""
    if not trades:
        return pd.DataFrame(), pd.Series(dtype=float)
    trades = sorted(trades, key=lambda t: (t["entry_date"], t["rank"]))
    taken, busy_until = [], []                 # exit dates of open positions
    held_symbols: dict[str, pd.Timestamp] = {}
    for t in trades:
        busy_until = [d for d in busy_until if d > t["entry_date"]]
        if held_symbols.get(t["symbol"], pd.Timestamp.min) > t["entry_date"]:
            continue
        if len(busy_until) >= slots:
            continue
        busy_until.append(t["exit_date"])
        held_symbols[t["symbol"]] = t["exit_date"]
        taken.append(t)
    cost = COST_BPS / 10_000
    daily: dict = {}
    for t in taken:
        prev = t["entry"] * (1 + cost)        # pay entry cost up front
        for k, (d, p) in enumerate(t["path"]):
            px = p * (1 - cost) if k == len(t["path"]) - 1 else p
            daily[d] = daily.get(d, 0.0) + (px / prev - 1) / slots
            prev = p
    s = pd.Series(daily).sort_index()
    return pd.DataFrame([{k: v for k, v in t.items() if k != "path"} for t in taken]), s


def stats(tr: pd.DataFrame, daily: pd.Series) -> dict:
    if tr.empty:
        return {"trades": 0}
    days = pd.bdate_range(daily.index.min(), daily.index.max())
    daily = daily.reindex(days, fill_value=0.0)
    eq = (1 + daily).cumprod()
    years = len(days) / 252
    wins, losses = tr[tr.ret > 0].ret, tr[tr.ret < 0].ret
    return {"trades": len(tr), "trades/yr": round(len(tr) / years, 1), "win%": round(100 * len(wins) / len(tr), 1),
            "avg_trade%": round(100 * tr.ret.mean(), 3), "avg_days": round(tr.days.mean(), 1),
            "pf": round(wins.sum() / -losses.sum(), 2) if len(losses) else np.inf,
            "CAGR%": round(100 * (eq.iloc[-1] ** (1 / years) - 1), 1),
            "maxDD%": round(100 * (eq / eq.cummax() - 1).min(), 1),
            "sharpe": round(daily.mean() / daily.std() * np.sqrt(252), 2) if daily.std() > 0 else np.nan,
            "exposure%": round(100 * (daily != 0).mean(), 0)}


def evaluate(trades: list[dict], period: str) -> dict:
    if period == "IS":
        trades = [t for t in trades if t["entry_date"] <= IS_END]
    elif period == "OOS":
        trades = [t for t in trades if t["entry_date"] > IS_END]
    tr, daily = portfolio(trades)
    return stats(tr, daily)


# ------------------------------------------------------------------------- strategies
def _scan(syms, only, signal_fn, rank_fn, max_hold, stop_atr, exit_fn, next_open, min_dollar_vol=2e7):
    trades = []
    for s in syms.values():
        if only and s.name not in only:
            continue
        I = s.ind
        with np.errstate(invalid="ignore"):
            sig = signal_fn(s, I) & (I["dollar_vol"] > min_dollar_vol) & np.isfinite(I["sma200"])
        for i in np.flatnonzero(sig):
            stop = s.C[i] - stop_atr * I["atr14"][i] if stop_atr else None
            t = walk(s, int(i), max_hold, stop, exit_fn, next_open)
            if t:
                t["rank"] = rank_fn(s, I, int(i))
                trades.append(t)
    return trades


def rsi_pullback(syms, only=None, rsi_max=10, trend="sma200", max_hold=5, stop_atr=None, next_open=False):
    """Connors-style: uptrend (close > SMA200), RSI(2) deeply oversold -> buy; exit when close > SMA5."""
    return _scan(syms, only,
                 lambda s, I: (s.C > I[trend]) & (I["rsi2"] < rsi_max),
                 lambda s, I, i: I["rsi2"][i],
                 max_hold, stop_atr, lambda s, j, e: s.C[j] > s.ind["sma5"][j], next_open)


def ibs_reversion(syms, only=None, ibs_max=0.2, max_hold=3, stop_atr=None, next_open=False):
    """Close near the day's low (IBS) in an uptrend -> buy; exit on first close in the upper half of the range."""
    return _scan(syms, only,
                 lambda s, I: (s.C > I["sma200"]) & (I["ibs"] < ibs_max) & (I["ret1"] < 0),
                 lambda s, I, i: I["ibs"][i],
                 max_hold, stop_atr, lambda s, j, e: s.ind["ibs"][j] > 0.6 or s.C[j] > s.H[j - 1], next_open)


def n_day_low(syms, only=None, n=10, max_hold=5, stop_atr=None, next_open=False):
    """Lowest close in n days while above the 200-day average -> buy; exit on a close above the 5-day average."""
    key = f"low{n}"
    return _scan(syms, only,
                 lambda s, I: (s.C > I["sma200"]) & (s.C <= I[key]),
                 lambda s, I, i: s.C[i] / I["sma200"][i],
                 max_hold, stop_atr, lambda s, j, e: s.C[j] > s.ind["sma5"][j], next_open)


def breakout_momentum(syms, only=None, vol_mult=2.0, max_hold=5, stop_atr=1.5, next_open=False):
    """New 20-day closing high on 2x volume -> ride it for up to max_hold days."""
    return _scan(syms, only,
                 lambda s, I: (s.C >= I["high20"]) & (s.V > vol_mult * I["vol20"]) & (s.C > I["sma50"]),
                 lambda s, I, i: -s.V[i] / s.ind["vol20"][i],
                 max_hold, stop_atr, lambda s, j, e: False, next_open)


def earnings_drift(syms, only=None, min_gap=0.04, vol_mult=3.0, max_hold=5, stop_atr=1.5, next_open=False):
    """Big gap up on huge volume (typically earnings) that closes strong -> hold for drift."""
    return _scan(syms, only,
                 lambda s, I: (I["gap"] > min_gap) & (s.V > vol_mult * I["vol20"]) & (I["ibs"] > 0.6),
                 lambda s, I, i: -s.ind["gap"][i],
                 max_hold, stop_atr, lambda s, j, e: False, next_open)


def random_entries(syms, only=None, p=0.02, max_hold=3, seed=0, next_open=False):
    rng = np.random.default_rng(seed)
    return _scan(syms, only, lambda s, I: rng.random(len(s.C)) < p, lambda s, I, i: rng.random(),
                 max_hold, None, lambda s, j, e: False, next_open)


GRIDS = {
    "rsi2_pullback": (rsi_pullback, {"rsi_max": [5, 10, 20], "trend": ["sma200", "sma50"], "max_hold": [3, 5, 10],
                                     "stop_atr": [None, 2.0, 3.0], "next_open": [False, True]}),
    "ibs_reversion": (ibs_reversion, {"ibs_max": [0.1, 0.2, 0.3], "max_hold": [1, 3, 5], "stop_atr": [None, 2.0],
                                      "next_open": [False, True]}),
    "n_day_low": (n_day_low, {"n": [5, 10], "max_hold": [3, 5, 10], "stop_atr": [None, 2.0, 3.0],
                              "next_open": [False, True]}),
    "breakout_momentum": (breakout_momentum, {"vol_mult": [1.5, 2.5], "max_hold": [3, 5, 10],
                                              "stop_atr": [1.0, 2.0], "next_open": [False, True]}),
    "earnings_drift": (earnings_drift, {"min_gap": [0.03, 0.06], "vol_mult": [2.0, 4.0], "max_hold": [3, 5, 10],
                                        "stop_atr": [1.0, 2.0], "next_open": [False, True]}),
}


def main():
    syms = load()
    lines = ["# Multi-day (swing) research", "",
             f"{len(syms)} symbols, daily bars (dividend-adjusted) 2016-2026. Costs {COST_BPS} bps per side, "
             f"{SLOTS} equal slots. Tuned on 2016-2021 only; 2022-2026 untouched.", "",
             "| strategy | universe | period | " + " | ".join(
                 ["trades", "trades/yr", "win%", "avg_trade%", "avg_days", "pf", "CAGR%", "maxDD%", "sharpe", "exposure%"]) + " |",
             "|" + "---|" * 13]
    chosen = []
    for name, (fn, grid) in GRIDS.items():
        best = (-np.inf, None, None)
        for combo in itertools.product(*grid.values()):
            p = dict(zip(grid, combo))
            trades = fn(syms, **p)
            s = evaluate(trades, "IS")
            if s.get("trades", 0) >= 100 and s["sharpe"] > best[0]:
                best = (s["sharpe"], p, trades)
        if best[1] is None:
            continue
        chosen.append((name, best[1]))
        etf_trades = fn(syms, only=set(ETFS), **best[1])
        for uni, tr in (("all", best[2]), ("ETFs only", etf_trades)):
            for per in ("IS", "OOS"):
                s = evaluate(tr, per)
                lines.append(f"| {name} | {uni} | {'2016-21' if per == 'IS' else '**2022-26 OOS**'} | "
                             + " | ".join(str(s.get(k, '')) for k in
                                          ["trades", "trades/yr", "win%", "avg_trade%", "avg_days", "pf", "CAGR%",
                                           "maxDD%", "sharpe", "exposure%"]) + " |")
        print(name, best[1], evaluate(best[2], "OOS"), flush=True)
    rnd = random_entries(syms)
    for per in ("IS", "OOS"):
        s = evaluate(rnd, per)
        lines.append(f"| baseline: random 3-day holds | all | {per} | " + " | ".join(str(s.get(k, '')) for k in
                     ["trades", "trades/yr", "win%", "avg_trade%", "avg_days", "pf", "CAGR%", "maxDD%", "sharpe", "exposure%"]) + " |")
    spy = syms["SPY"]
    for per, mask in (("IS", spy.dates <= np.datetime64(IS_END.date())), ("OOS", spy.dates > np.datetime64(IS_END.date()))):
        c = spy.C[mask]
        yrs = len(c) / 252
        eq = c / c[0]
        lines.append(f"| reference: buy & hold SPY | SPY | {per} | | | | | | | {round(100*(eq[-1]**(1/yrs)-1),1)} | "
                     f"{round(100*(eq/np.maximum.accumulate(eq)-1).min(),1)} | | 100 |")
    lines += ["", "## Chosen settings (picked on 2016-2021 only)", ""] + [f"- **{n}**: `{p}`" for n, p in chosen]
    out = Path(__file__).with_name("RESULTS_SWING.md")
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
