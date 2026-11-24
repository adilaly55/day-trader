"""Tune each strategy on 2021-2023 only, then score the chosen settings on 2024-2026.

Writes research/RESULTS.md. Usage: python run_research.py
"""
from __future__ import annotations

import itertools
import time
from pathlib import Path

import pandas as pd

import lab
import strategies as st

SLOTS = 5          # account split into 5 equal slots -> up to 5 trades a day
MIN_IS_TRADES = 150

GRIDS = {
    "orb_in_play": (st.orb_in_play, {
        "or_bars": [1, 3, 6], "min_rvol": [1.5, 2.5, 4.0], "stop_atr": [0.1, 0.2, 0.35],
        "target_r": [None, 2.0, 4.0], "vwap_filter": [False, True], "use_regime": [False, True]}),
    "gap_and_go": (st.gap_and_go, {
        "min_gap": [0.02, 0.04], "min_rvol": [2.0, 4.0], "target_r": [None, 1.0, 2.0], "use_regime": [False, True]}),
    "gap_down_reversal": (st.gap_down_reversal, {
        "max_gap": [-0.02, -0.04], "fill_target": [False, True], "use_regime": [False, True]}),
    "vwap_pullback": (st.vwap_pullback, {
        "min_move": [0.01, 0.02], "min_rvol": [1.5, 2.5], "target_r": [None, 1.5, 3.0], "use_regime": [False, True]}),
}
BASELINES = {
    "baseline: random entries": (st.random_entries, {}),
    "baseline: buy SPY 9:35, sell 12:30": (st.spy_morning, {}),
}


def score(trades: pd.DataFrame) -> float:
    s = lab.stats(trades, SLOTS)
    if s.get("trades", 0) < MIN_IS_TRADES:
        return float("-inf")
    return s["sharpe"]


def main():
    t0 = time.time()
    syms = lab.load()
    market = syms["SPY"]
    print(f"loaded {len(syms)} symbols in {time.time()-t0:.0f}s")
    lines = ["# Backtest results", "",
             f"{len(syms)} symbols, 5-minute bars 09:30-12:30 ET, {lab.START:%Y-%m-%d} to latest. "
             f"Costs {lab.COST_BPS} bps per side. Up to {SLOTS} trades/day, equal size. "
             "Parameters chosen on 2021-2023 ONLY; 2024-2026 is untouched out-of-sample.", ""]
    summary = []
    all_trades = {}
    for name, (fn, grid) in GRIDS.items():
        keys = list(grid)
        best = (float("-inf"), None, None)
        tried = 0
        for combo in itertools.product(*grid.values()):
            params = dict(zip(keys, combo))
            trades = fn(syms, market, **params)
            tried += 1
            if trades.empty:
                continue
            sc = score(trades[trades.date <= lab.IS_END])
            if sc > best[0]:
                best = (sc, params, trades)
        print(f"{name}: tried {tried} settings, best IS sharpe {best[0]:.2f} {best[1]}  ({time.time()-t0:.0f}s)")
        if best[1] is None:
            continue
        all_trades[name] = best[2]
        rep = lab.split_report(name, best[2], SLOTS)
        rep["params"] = str(best[1])
        rep["settings_tried"] = tried
        summary.append(rep)
    for name, (fn, kw) in BASELINES.items():
        trades = fn(syms, market, **kw)
        all_trades[name] = trades
        summary.append(lab.split_report(name, trades, SLOTS))

    table = pd.concat(summary, ignore_index=True)
    lines += ["## Summary", "", table.drop(columns=["params", "settings_tried"], errors="ignore").to_markdown(index=False), ""]
    lines += ["## Chosen settings (picked on 2021-2023 only)", ""]
    for _, r in table.dropna(subset=["params"]).drop_duplicates("strategy").iterrows():
        lines.append(f"- **{r.strategy}** ({int(r.settings_tried)} settings tried): `{r.params}`")
    lines.append("")
    for name, trades in all_trades.items():
        lines += [f"## {name}: by year", "", lab.by_year(trades, SLOTS).to_markdown(index=False), ""]
    out = Path(__file__).with_name("RESULTS.md")
    out.write_text("\n".join(lines))
    print(table.drop(columns=["params"], errors="ignore").to_string())
    print(f"\nwrote {out} in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
