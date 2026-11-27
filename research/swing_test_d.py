"""Test D: safety rules on the lead strategy (RSI2 pullback, realistic 15:45/15:55 timing, 2016 S&P 100 stocks).
  * disaster stops (ATR- and percent-based)
  * earnings filter. Free data has no historical earnings calendar, so earnings days are detected after the fact
    as 'event days' (volume > 3x its 20-day average and a >3% gap). Live, the Finnhub calendar knows them in advance,
    so this measures what a correct calendar filter would do.
"""
import numpy as np
import swing as sw
from swing_test_c import U, start, COLS

P = {'rsi_max': 20, 'trend': 'sma200', 'max_hold': 5, 'next_open': True}
for s in U.values():
    vol20 = np.convolve(s.V, np.ones(20) / 20, mode="full")[:len(s.V)]
    vol20 = np.concatenate([[np.nan], vol20[:-1]])
    gap = np.concatenate([[np.nan], s.O[1:] / s.C[:-1] - 1])
    with np.errstate(invalid="ignore"):
        s.ind["event"] = ((s.V > 3 * vol20) & (np.abs(gap) > 0.03)).astype(float)


def skip_hold(s, i):            # an event during the holding window (entry day .. +5)
    return bool(np.nansum(s.ind["event"][i + 1:i + 7]) > 0)


def skip_hold_or_signal(s, i):  # ...or the dip itself was caused by an event (signal day or day before)
    return skip_hold(s, i) or bool(np.nansum(s.ind["event"][max(0, i - 1):i + 1]) > 0)


variants = [
    ("no safety rules (Test C)", None, None, None),
    ("stop 2 ATR", 2.0, None, None),
    ("stop 3 ATR", 3.0, None, None),
    ("stop 8%", None, 0.08, None),
    ("stop 12%", None, 0.12, None),
    ("skip earnings in hold window", None, None, skip_hold),
    ("skip earnings in hold + earnings-caused dips", None, None, skip_hold_or_signal),
    ("skip earnings (both) + stop 3 ATR", 3.0, None, skip_hold_or_signal),
    ("skip earnings (both) + stop 12%", None, 0.12, skip_hold_or_signal),
]
out = ["", "---", "# Test D: safety rules (RSI2 pullback, realistic timing, 10 bps/side costs)", "",
       "| variant | period | " + " | ".join(COLS) + " | worst trade % |", "|" + "---|" * (len(COLS) + 3)]
sw.COST_BPS = 10
for label, atr, pct, skip in variants:
    sw.STOP_PCT, sw.SKIP = pct, skip
    tr = [t for t in sw.rsi_pullback(U, stop_atr=atr, **P) if t["entry_date"] >= start]
    for per, lab in (("IS", "2021"), ("OOS", "**2022-26**")):
        taken, daily = sw.portfolio([t for t in tr if (t["entry_date"] > sw.IS_END) == (per == "OOS")])
        st = sw.stats(taken, daily)
        worst = round(100 * taken.ret.min(), 1) if len(taken) else ""
        out.append(f"| {label} | {lab} | " + " | ".join(str(st.get(k, '')) for k in COLS) + f" | {worst} |")
sw.STOP_PCT, sw.SKIP, sw.COST_BPS = None, None, 5
with open("RESULTS_SWING.md", "a") as f:
    f.write("\n".join(out) + "\n")
print("\n".join(out))
