"""Research lab: fast, lookahead-free backtests of long-only intraday strategies.

Data model
  For every symbol we build arrays of shape [days, 36]: the 36 five-minute bars from
  09:30 to 12:30 ET (the bot's trading window = 18:30-21:30 Dubai in winter).
  Daily features (gap, ATR, trend, relative volume...) only use information known
  at the moment of the decision.

Execution model (deliberately conservative)
  * Entries happen at the CLOSE of the bar that triggers the signal (a market order
    sent when the bar completes).
  * Stops/targets are checked on later bars. If a bar touches both, we assume the
    stop was hit first. A gap through the stop exits at the bar's open.
  * Anything still open is sold at the 12:30 ET close.
  * Costs: COST_BPS per side (spread + slippage). Trading 212 charges no commission
    and a USD account pays no FX fee.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
NBARS = 36
COST_BPS = 5.0
IS_END = pd.Timestamp("2023-12-31")          # in-sample: 2021-2023, out-of-sample: 2024+
START = pd.Timestamp("2021-01-01")


@dataclass
class Sym:
    name: str
    dates: np.ndarray        # datetime64[D], shape [D]
    O: np.ndarray            # [D, 36]
    H: np.ndarray
    L: np.ndarray
    C: np.ndarray
    V: np.ndarray
    VWAP: np.ndarray         # cumulative session VWAP at the close of each bar
    feat: pd.DataFrame       # daily features indexed by date (known before/at the open)


def _daily_features(daily: pd.DataFrame, first_bar_vol: pd.Series, first_open: pd.Series) -> pd.DataFrame:
    d = daily.set_index(pd.to_datetime(daily["date"])).sort_index()
    pc = d["close"].shift(1)
    tr = pd.concat([d["high"] - d["low"], (d["high"] - pc).abs(), (d["low"] - pc).abs()], axis=1).max(axis=1)
    f = pd.DataFrame(index=d.index)
    f["prev_close"] = pc
    f["atr14"] = tr.rolling(14).mean().shift(1)
    f["avg_vol20"] = d["volume"].rolling(20).mean().shift(1)
    f["sma20"] = d["close"].rolling(20).mean().shift(1)
    f["sma50"] = d["close"].rolling(50).mean().shift(1)
    f["ret5d"] = (d["close"] / d["close"].shift(5) - 1).shift(1)
    f["premarket_volume"] = d["premarket_volume"]
    f["open"] = first_open.reindex(f.index)
    f["gap"] = f["open"] / f["prev_close"] - 1
    fbv = first_bar_vol.reindex(f.index)
    f["first_bar_vol"] = fbv
    f["rvol5"] = fbv / fbv.rolling(14, min_periods=10).mean().shift(1)   # first 5 min vs its usual
    f["pm_rvol"] = f["premarket_volume"] / f["premarket_volume"].rolling(14, min_periods=10).mean().shift(1)
    return f


def load(symbols: list[str] | None = None) -> dict[str, Sym]:
    files = sorted((DATA / "5min").glob("*.parquet"))
    out = {}
    for fp in files:
        name = fp.stem
        if symbols and name not in symbols:
            continue
        df = pd.read_parquet(fp)
        df["date"] = df["ts"].dt.tz_localize(None).dt.normalize()
        df["slot"] = ((df["ts"].dt.hour * 60 + df["ts"].dt.minute) - 570) // 5
        df = df[(df["slot"] >= 0) & (df["slot"] < NBARS)]
        piv = {c: df.pivot_table(index="date", columns="slot", values=c, aggfunc="last").reindex(columns=range(NBARS))
               for c in ("open", "high", "low", "close", "volume", "vwap")}
        # need a real first bar; fill rare missing later bars with the previous close and zero volume
        ok = piv["open"][0].notna() & (piv["volume"].notna().sum(axis=1) >= 30)
        for c in piv:
            piv[c] = piv[c][ok]
        C = piv["close"].ffill(axis=1)
        O = piv["open"].fillna(C.shift(1, axis=1)).fillna(C)
        H = piv["high"].fillna(np.maximum(O, C))
        L = piv["low"].fillna(np.minimum(O, C))
        V = piv["volume"].fillna(0)
        VW = piv["vwap"].fillna(C)
        cum_pv = (VW * V).cumsum(axis=1)
        cum_v = V.cumsum(axis=1).replace(0, np.nan)
        SV = (cum_pv / cum_v).ffill(axis=1).fillna(C)
        daily = pd.read_parquet(DATA / "daily" / f"{name}.parquet")
        feat = _daily_features(daily, V[0], O[0])
        dates = C.index
        keep = dates >= START
        out[name] = Sym(name, dates[keep].values.astype("datetime64[D]"),
                        O.values[keep], H.values[keep], L.values[keep], C.values[keep], V.values[keep],
                        SV.values[keep], feat.reindex(dates[keep]))
    return out


# --------------------------------------------------------------------------- simulation
def simulate(s: Sym, d: int, entry_bar: int, stop: float, target: float | None,
             exit_bar: int = NBARS - 1) -> tuple[float, float, str]:
    """Buy at close of entry_bar; return (entry_price, exit_price, reason)."""
    entry = s.C[d, entry_bar]
    for b in range(entry_bar + 1, exit_bar + 1):
        o, h, l = s.O[d, b], s.H[d, b], s.L[d, b]
        if o <= stop:
            return entry, o, "stop"
        if l <= stop:
            return entry, stop, "stop"
        if target is not None:
            if o >= target:
                return entry, o, "target"
            if h >= target:
                return entry, target, "target"
    return entry, s.C[d, exit_bar], "time"


def trade_row(s: Sym, d: int, entry_bar: int, stop: float, target: float | None, **extra) -> dict:
    entry, exit_, reason = simulate(s, d, entry_bar, stop, target)
    gross = exit_ / entry - 1
    net = gross - 2 * COST_BPS / 10_000
    risk = (entry - stop) / entry
    return {"symbol": s.name, "date": pd.Timestamp(s.dates[d]), "entry_bar": entry_bar, "entry": entry,
            "exit": exit_, "reason": reason, "ret": net, "r": net / risk if risk > 0 else np.nan, **extra}


# --------------------------------------------------------------------------- reporting
def daily_portfolio(trades: pd.DataFrame, slots: int = 5) -> pd.Series:
    """Daily % return of an account split into `slots` equal parts, taking the best-ranked
    `slots` trades each day (by the strategy's 'rank' column, lower = better)."""
    if trades.empty:
        return pd.Series(dtype=float)
    t = trades.sort_values(["date", "rank"]).groupby("date").head(slots)
    return t.groupby("date")["ret"].sum() / slots


def stats(trades: pd.DataFrame, slots: int = 5) -> dict:
    if trades.empty:
        return {"trades": 0}
    t = trades.sort_values(["date", "rank"]).groupby("date").head(slots)
    daily = t.groupby("date")["ret"].sum() / slots
    all_days = pd.bdate_range(t["date"].min(), t["date"].max())
    daily = daily.reindex(all_days, fill_value=0.0)
    eq = (1 + daily).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    wins, losses = t[t.ret > 0].ret, t[t.ret < 0].ret
    years = len(all_days) / 252
    return {
        "trades": len(t),
        "trades/day": round(len(t) / len(all_days), 2),
        "win%": round(100 * len(wins) / len(t), 1),
        "avg_trade%": round(100 * t.ret.mean(), 3),
        "pf": round(wins.sum() / -losses.sum(), 2) if len(losses) else np.inf,
        "avg_R": round(t.r.mean(), 3),
        "CAGR%": round(100 * (eq.iloc[-1] ** (1 / years) - 1), 1) if years > 0 else np.nan,
        "maxDD%": round(100 * dd, 1),
        "sharpe": round(daily.mean() / daily.std() * np.sqrt(252), 2) if daily.std() > 0 else np.nan,
    }


def split_report(name: str, trades: pd.DataFrame, slots: int = 5) -> pd.DataFrame:
    rows = []
    for label, part in (("in-sample 2021-23", trades[trades.date <= IS_END]),
                        ("OUT-OF-SAMPLE 2024-26", trades[trades.date > IS_END])):
        rows.append({"strategy": name, "period": label, **stats(part, slots)})
    return pd.DataFrame(rows)


def by_year(trades: pd.DataFrame, slots: int = 5) -> pd.DataFrame:
    return pd.DataFrame([{"year": y, **stats(g, slots)} for y, g in trades.groupby(trades.date.dt.year)])
