"""Stress tests for the research results. Appends to research/RESULTS.md.

1. Is the ORB edge robust, or one lucky setting out of 324?  (IS vs OOS across the whole grid)
2. How much does it depend on trading costs?
3. Machine-learning "prediction engine": gradient boosting on stock-day features at 09:35,
   trained on 2021-2023, tested on 2024-2026 (walk-forward, yearly retrain).
"""
from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

import lab
import strategies as st
from run_research import GRIDS, SLOTS

OUT = Path(__file__).with_name("RESULTS.md")


def grid_robustness(syms, market, lines):
    fn, grid = GRIDS["orb_in_play"]
    rows = []
    for combo in itertools.product(*grid.values()):
        p = dict(zip(grid, combo))
        t = fn(syms, market, **p)
        if t.empty:
            continue
        a, b = lab.stats(t[t.date <= lab.IS_END], SLOTS), lab.stats(t[t.date > lab.IS_END], SLOTS)
        if a.get("trades", 0) < 100 or b.get("trades", 0) < 100:
            continue
        rows.append({**p, "is_trade%": a["avg_trade%"], "oos_trade%": b["avg_trade%"],
                     "is_sharpe": a["sharpe"], "oos_sharpe": b["sharpe"]})
    g = pd.DataFrame(rows)
    corr = g["is_sharpe"].corr(g["oos_sharpe"], method="spearman")
    top = g.sort_values("is_sharpe", ascending=False).head(20)
    lines += ["## Stress test 1: is the ORB edge robust?", "",
              f"- Settings with enough trades: {len(g)}",
              f"- Share with positive OUT-OF-SAMPLE avg trade (after costs): {100*(g['oos_trade%']>0).mean():.0f}%",
              f"- Among the 20 best in-sample settings, positive out-of-sample: {(top['oos_trade%']>0).sum()}/20, "
              f"median OOS avg trade {top['oos_trade%'].median():+.3f}%",
              f"- Rank correlation in-sample vs out-of-sample Sharpe: {corr:.2f} (1 = in-sample perfectly predicts OOS, 0 = no relation)",
              "", "Average out-of-sample result by setting (each row averages over all other settings):", ""]
    for k in ("or_bars", "min_rvol", "stop_atr", "target_r", "vwap_filter", "use_regime"):
        m = g.groupby(k, dropna=False)[["is_trade%", "oos_trade%", "oos_sharpe"]].mean().round(3)
        lines += [f"**{k}**", "", m.to_markdown(), ""]
    return g


def cost_sensitivity(syms, market, params, lines):
    lines += ["## Stress test 2: trading-cost sensitivity (chosen ORB settings)", "",
              "| cost per side | OOS avg trade % | OOS profit factor | OOS Sharpe |", "|---|---|---|---|"]
    orig = lab.COST_BPS
    for c in (0, 2, 5, 10, 15):
        lab.COST_BPS = c
        t = st.orb_in_play(syms, market, **params)
        s = lab.stats(t[t.date > lab.IS_END], SLOTS)
        lines.append(f"| {c} bps | {s['avg_trade%']:+.3f} | {s['pf']} | {s['sharpe']} |")
    lab.COST_BPS = orig
    lines.append("")


# ---------------------------------------------------------------------------- ML model
FEATURES = ["gap", "rvol5", "pm_rvol", "bar0_ret", "bar0_range_atr", "atr_pct", "ret5d", "vs_sma20", "vs_sma50",
            "spy_gap", "spy_bar0_ret", "spy_trend", "dollar_vol_log"]


def ml_dataset(syms, market) -> pd.DataFrame:
    spy = {"gap": dict(zip(market.dates.tolist(), market.F["gap"])),
           "bar0": dict(zip(market.dates.tolist(), market.C[:, 0] / market.O[:, 0] - 1)),
           "trend": dict(zip(market.dates.tolist(), (market.F["prev_close"] > market.F["sma20"]).astype(float)))}
    frames = []
    for s in syms.values():
        if s.name == "SPY":
            continue
        F = s.F
        ok = st._eligible_mask(s)
        dl = s.dates.tolist()
        df = pd.DataFrame({
            "symbol": s.name, "date": pd.to_datetime(s.dates),
            "gap": F["gap"], "rvol5": F["rvol5"], "pm_rvol": F["pm_rvol"],
            "bar0_ret": s.C[:, 0] / s.O[:, 0] - 1,
            "bar0_range_atr": (s.H[:, 0] - s.L[:, 0]) / F["atr14"],
            "atr_pct": F["atr14"] / F["prev_close"], "ret5d": F["ret5d"],
            "vs_sma20": F["prev_close"] / F["sma20"] - 1, "vs_sma50": F["prev_close"] / F["sma50"] - 1,
            "spy_gap": [spy["gap"].get(d, np.nan) for d in dl],
            "spy_bar0_ret": [spy["bar0"].get(d, np.nan) for d in dl],
            "spy_trend": [spy["trend"].get(d, np.nan) for d in dl],
            "dollar_vol_log": np.log10(F["avg_vol20"] * F["prev_close"]),
            # target: buy at 09:35 close, sell at 12:30 close, net of costs
            "ret": s.C[:, -1] / s.C[:, 0] - 1 - 2 * lab.COST_BPS / 10_000,
            # protective version: stop 0.5 ATR below entry (what the bot would actually do)
            "ret_stop": [_stop_ret(s, d) for d in range(len(s.dates))],
        })
        frames.append(df[ok])
    return pd.concat(frames, ignore_index=True).replace([np.inf, -np.inf], np.nan)


def _stop_ret(s, d):
    entry = s.C[d, 0]
    stop = entry - 0.5 * s.F["atr14"][d]
    _, exit_, _ = lab.simulate(s, d, 0, stop, None)
    return exit_ / entry - 1 - 2 * lab.COST_BPS / 10_000


def ml_walk_forward(data: pd.DataFrame, lines):
    preds = []
    for test_year in (2024, 2025, 2026):
        train = data[data.date.dt.year < test_year].dropna(subset=["ret"])
        test = data[data.date.dt.year == test_year].copy()
        model = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.03, max_leaf_nodes=15,
                                              min_samples_leaf=200, l2_regularization=1.0, random_state=0)
        model.fit(train[FEATURES], train["ret"].clip(-0.1, 0.1))
        test["pred"] = model.predict(test[FEATURES])
        preds.append(test)
    p = pd.concat(preds)
    lines += ["## Stress test 3: machine-learning prediction engine", "",
              "Gradient-boosted trees on 13 features known at 09:35 (gap, relative volume, first-bar move, "
              "trend, volatility, market direction...). Predicts each stock's 09:35 -> 12:30 return. "
              "Retrained every year on all prior years; scored only on the following year (never seen).", "",
              f"- Stock-days scored out-of-sample: {len(p):,}",
              f"- Correlation of prediction with actual return: {p['pred'].corr(p['ret']):.3f} "
              f"(rank: {p['pred'].corr(p['ret'], method='spearman'):.3f})", "",
              "Actual average return (after costs) by prediction bucket, out-of-sample:", "",
              "| prediction decile | avg return % (hold to 12:30) | avg return % (with 0.5 ATR stop) | win % |",
              "|---|---|---|---|"]
    p["decile"] = p.groupby(p.date.dt.year)["pred"].transform(lambda x: pd.qcut(x, 10, labels=False, duplicates="drop"))
    for dec, g in p.groupby("decile"):
        lines.append(f"| {int(dec)+1} {'(most bullish)' if dec == 9 else '(most bearish)' if dec == 0 else ''} | "
                     f"{100*g['ret'].mean():+.3f} | {100*g['ret_stop'].mean():+.3f} | {100*(g['ret']>0).mean():.1f} |")
    # trading rule: each day take the top-5 predictions, only if prediction > 0
    top = p[p.pred > 0].sort_values(["date", "pred"], ascending=[True, False]).groupby("date").head(SLOTS)
    t = top.rename(columns={"ret_stop": "_rs"}).assign(ret=top["ret_stop"], r=np.nan, rank=-top["pred"])
    s = lab.stats(t, SLOTS)
    lines += ["", f"**Trading rule** (each day buy the top {SLOTS} predictions if > 0, 0.5 ATR stop, sell 12:30), "
              f"2024-2026 out-of-sample: {s}", ""]
    by_year = lab.by_year(t, SLOTS)
    lines += [by_year.to_markdown(index=False), ""]


def main():
    syms = lab.load()
    market = syms["SPY"]
    lines = ["", "---", "# Stress tests", ""]
    grid_robustness(syms, market, lines)
    best = {"or_bars": 1, "min_rvol": 4.0, "stop_atr": 0.2, "target_r": None, "vwap_filter": False, "use_regime": True}
    cost_sensitivity(syms, market, best, lines)
    data = ml_dataset(syms, market)
    ml_walk_forward(data, lines)
    with OUT.open("a") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
