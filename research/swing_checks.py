"""Robustness checks for the best swing candidates on ETFs (no survivorship bias)."""
import pandas as pd
import swing as sw
from universe import ETFS

syms = sw.load()
ETF = set(ETFS)
CANDS = {
    "rsi2_pullback": (sw.rsi_pullback, {'rsi_max': 20, 'trend': 'sma200', 'max_hold': 5, 'stop_atr': None, 'next_open': True}),
    "n_day_low": (sw.n_day_low, {'n': 5, 'max_hold': 10, 'stop_atr': None, 'next_open': True}),
    "ibs_reversion": (sw.ibs_reversion, {'ibs_max': 0.3, 'max_hold': 5, 'stop_atr': None, 'next_open': True}),
}
out = ["", "---", "# Swing robustness checks (ETFs only)", ""]
for name, (fn, p) in CANDS.items():
    out += [f"## {name}", "", "| variant | period | trades | win% | avg_trade% | pf | CAGR% | maxDD% | sharpe |", "|---|---|---|---|---|---|---|---|---|"]
    for label, cost, exit_open, stop in (("baseline (5 bps, exit at close)", 5, False, None),
                                         ("exit at NEXT OPEN (no close peeking)", 5, True, None),
                                         ("costs 10 bps/side", 10, False, None),
                                         ("costs 10 bps + next-open exit", 10, True, None),
                                         ("with 3 ATR protective stop", 5, False, 3.0)):
        sw.COST_BPS, sw.EXIT_NEXT_OPEN = cost, exit_open
        tr = fn(syms, only=ETF, **{**p, "stop_atr": stop})
        for per in ("IS", "OOS"):
            s = sw.evaluate(tr, per)
            out.append(f"| {label} | {per} | " + " | ".join(str(s.get(k)) for k in ["trades", "win%", "avg_trade%", "pf", "CAGR%", "maxDD%", "sharpe"]) + " |")
    sw.COST_BPS, sw.EXIT_NEXT_OPEN = 5, False
    tr = fn(syms, only=ETF, **p)
    t, daily = sw.portfolio(tr)
    yrs = []
    for y, g in t.groupby(t.entry_date.dt.year):
        dy = daily[daily.index.year == y]
        st = sw.stats(g, dy)
        yrs.append({"year": y, **{k: st[k] for k in ["trades", "win%", "avg_trade%", "CAGR%", "maxDD%"]}})
    out += ["", "By year (baseline variant):", "", pd.DataFrame(yrs).to_markdown(index=False), ""]
with open("RESULTS_SWING.md", "a") as f:
    f.write("\n".join(out) + "\n")
print("\n".join(out))
