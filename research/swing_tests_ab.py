"""Test A: ETF dip-buying executed at the LONDON close (UCITS ETFs on Trading 212).
   Test B: dip-buying on US stocks using the 2016 S&P 100 list (survivorship-reduced)."""
from datetime import datetime, time
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import swing as sw
from universe import SP100_2016

LON, NY = ZoneInfo("Europe/London"), ZoneInfo("America/New_York")
PARAMS = {
    "n_day_low": (sw.n_day_low, {'n': 5, 'max_hold': 10, 'stop_atr': None}),
    "rsi2_pullback": (sw.rsi_pullback, {'rsi_max': 20, 'trend': 'sma200', 'max_hold': 5, 'stop_atr': None}),
}
COLS = ["trades", "trades/yr", "win%", "avg_trade%", "avg_days", "pf", "CAGR%", "maxDD%", "sharpe", "exposure%"]
out = []


def row(label, per, s):
    return f"| {label} | {per} | " + " | ".join(str(s.get(k, "")) for k in COLS) + " |"


def header(title):
    return ["", f"## {title}", "", "| variant | period | " + " | ".join(COLS) + " |", "|" + "---|" * (len(COLS) + 2)]


# ---------------------------------------------------------------- Test A
def london_series(sym, lag_min=10):
    df = pd.read_parquet(f"../data/5min_full/{sym}.parquet")
    df["date"] = df["ts"].dt.tz_localize(None).dt.normalize()
    df["end"] = df["ts"] + pd.Timedelta(minutes=5)
    rows = []
    for d, g in df.groupby("date"):
        lc = datetime.combine(d.date(), time(16, 30), LON).astimezone(NY)
        lc = pd.Timestamp(lc)
        dec = g[g["end"] <= lc - pd.Timedelta(minutes=lag_min)]
        exe = g[g["end"] <= lc]
        if dec.empty or exe.empty:
            continue
        rows.append({"date": d, "dec": dec["close"].iloc[-1], "exec": exe["close"].iloc[-1],
                     "low": g[g["end"] <= lc]["low"].min(), "high": g[g["end"] <= lc]["high"].max(),
                     "open": g["open"].iloc[0], "vol": g[g["end"] <= lc]["volume"].sum()})
    return pd.DataFrame(rows)


def make_d(sym, ser):
    c = ser["dec"]
    ind = {"sma5": c.rolling(5).mean(), "sma200": c.rolling(200).mean(), "sma50": c.rolling(50).mean(),
           "rsi2": sw._rsi(c, 2), "low5": c.rolling(5).min(), "low10": c.rolling(10).min(),
           "atr14": (ser["high"] - ser["low"]).rolling(14).mean(),
           "dollar_vol": pd.Series(np.full(len(c), 1e12))}       # ETFs: always liquid enough
    return sw.D(sym, ser["date"].values.astype("datetime64[D]"), ser["open"].values, ser["high"].values,
                ser["low"].values, c.values, ser["vol"].values.astype(float),
                {k: v.to_numpy(dtype=float) for k, v in ind.items()}, X=ser["exec"].values)


etfs = ["SPY", "QQQ", "XLK", "XLF", "XLV", "SMH", "GLD", "TLT"]
L = {s: make_d(s, london_series(s)) for s in etfs}
first_valid = max(pd.Timestamp(d.dates[199]) for d in L.values())
out += ["# Tests A & B", "", f"Test A data: {', '.join(etfs)} 5-min bars; signals at London close -10 min, "
        f"executed at the London close (16:30 London). Valid from {first_valid:%Y-%m-%d} (needs 200 days of history)."]
for name, (fn, p) in PARAMS.items():
    out += header(f"A. {name}: UCITS ETFs at the London close (~20:30 Dubai)")
    for cost in (5, 10, 15, 30):
        sw.COST_BPS = cost
        tr = [t for t in fn(L, **p, next_open=False) if t["entry_date"] >= first_valid]
        lab = f"cost {cost} bps/side" + (" (= 0.15% FX fee each way + spread)" if cost == 30 else "")
        for per in ("IS", "OOS"):
            out.append(row(lab, "2021" if per == "IS" else "**2022-26**", sw.evaluate(tr, per)))
sw.COST_BPS = 5

# ---------------------------------------------------------------- Test B
syms = sw.load()
SP = set(SP100_2016)
out += ["", f"Test B universe: {len(SP & set(syms))} stocks of the 2016 S&P 100 (includes later losers: GE, INTC, WBA, "
        "MMM, BA, PYPL, VZ, T, KHC, CVS, NKE...). Executed at the US close."]
for name, (fn, p) in list(PARAMS.items()) + [("random 3-day holds (baseline)", (sw.random_entries, {}))]:
    out += header(f"B. {name}: 2016 S&P 100 stocks")
    for label, cost, exit_open in (("5 bps, exit at close", 5, False), ("5 bps, exit next open", 5, True),
                                   ("10 bps, exit at close", 10, False)):
        sw.COST_BPS, sw.EXIT_NEXT_OPEN = cost, exit_open
        kw = dict(p)
        if "random" not in name:
            kw["next_open"] = True
        tr = fn(syms, only=SP, **kw)
        for per in ("IS", "OOS"):
            out.append(row(label, "2016-21" if per == "IS" else "**2022-26**", sw.evaluate(tr, per)))
sw.COST_BPS, sw.EXIT_NEXT_OPEN = 5, False
with open("RESULTS_SWING.md", "a") as f:
    f.write("\n---\n" + "\n".join(out) + "\n")
print("\n".join(out))
