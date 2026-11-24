"""Test C: realistic execution for US stocks. Signals computed on the 15:45 ET price, orders filled at the
15:55 ET price (exits) and the 09:30 open (entries) -- what the bot can really do. 5-min data from 2020-06."""
import numpy as np
import pandas as pd
import swing as sw
from universe import SP100_2016
from pathlib import Path

COLS = ["trades", "trades/yr", "win%", "avg_trade%", "avg_days", "pf", "CAGR%", "maxDD%", "sharpe", "exposure%"]


def series(sym, dec_end="15:45", exe_end="15:55"):
    df = pd.read_parquet(f"../data/5min_full/{sym}.parquet")
    df["date"] = df["ts"].dt.tz_localize(None).dt.normalize()
    df["end"] = (df["ts"] + pd.Timedelta(minutes=5)).dt.strftime("%H:%M")
    g = df.groupby("date")
    dec = df[df["end"] <= dec_end].groupby("date")["close"].last()
    exe = df[df["end"] <= exe_end].groupby("date")["close"].last()
    o = g["open"].first()
    hi = df[df["end"] <= dec_end].groupby("date")["high"].max()
    lo = df[df["end"] <= dec_end].groupby("date")["low"].min()
    vol = df[df["end"] <= dec_end].groupby("date")["volume"].sum()
    s = pd.DataFrame({"dec": dec, "exec": exe, "open": o, "high": hi, "low": lo, "vol": vol}).dropna()
    return s[s["exec"].notna()].reset_index()


def make(sym, s):
    c = s["dec"]
    ind = {"sma5": c.rolling(5).mean(), "sma200": c.rolling(200).mean(), "sma50": c.rolling(50).mean(),
           "rsi2": sw._rsi(c, 2), "low5": c.rolling(5).min(), "low10": c.rolling(10).min(),
           "atr14": (s["high"] - s["low"]).rolling(14).mean(), "dollar_vol": (c * s["vol"]).rolling(20).mean()}
    d = sw.D(sym, s["date"].values.astype("datetime64[D]"), s["open"].values, s["high"].values, s["low"].values,
             c.values, s["vol"].values.astype(float), {k: v.to_numpy(dtype=float) for k, v in ind.items()},
             X=s["exec"].values)
    return d


have = {p.stem for p in Path("../data/5min_full").glob("*.parquet")}
names = sorted(set(SP100_2016) & have)
U = {n: make(n, series(n)) for n in names}
start = max(pd.Timestamp(u.dates[199]) for u in U.values())
out = ["", "---", "# Test C: realistic execution (decide 15:45 ET, fill 15:55 ET; entries at 09:30 open)", "",
       f"{len(names)} of the 2016 S&P 100 stocks with 5-min data: {', '.join(names)}. From {start:%Y-%m-%d}. "
       "Parameters fixed from the 2016-2021 daily tuning (no re-tuning).", ""]
cases = {
    "rsi2_pullback": (sw.rsi_pullback, {'rsi_max': 20, 'trend': 'sma200', 'max_hold': 5, 'stop_atr': None}),
    "n_day_low": (sw.n_day_low, {'n': 5, 'max_hold': 10, 'stop_atr': None}),
    "random 3-day holds": (sw.random_entries, {}),
}
for name, (fn, p) in cases.items():
    out += [f"## {name}", "", "| entry | cost | period | " + " | ".join(COLS) + " |", "|" + "---|" * (len(COLS) + 3)]
    for entry_open in (True, False):
        for cost in (5, 10):
            sw.COST_BPS = cost
            tr = [t for t in fn(U, **p, next_open=entry_open) if t["entry_date"] >= start]
            for per, lab in (("IS", "2021"), ("OOS", "**2022-26**")):
                s = sw.evaluate(tr, per)
                out.append(f"| {'09:30 open next day' if entry_open else '15:55 same day'} | {cost} bps | {lab} | "
                           + " | ".join(str(s.get(k, '')) for k in COLS) + " |")
    out.append("")
sw.COST_BPS = 5
with open("RESULTS_SWING.md", "a") as f:
    f.write("\n".join(out) + "\n")
print("\n".join(out))
