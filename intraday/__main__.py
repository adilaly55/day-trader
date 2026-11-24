"""Command line entry point:  python -m intraday {backtest,fetch,live,report} ..."""
from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from .broker import PaperBroker
from .config import Config
from .data import csv_bars, synthetic_bars
from .engine import Engine
from .models import Trade
from .tracker import Tracker, format_summary, summarize


def cmd_backtest(args):
    cfg = Config.load(args.config)
    if args.symbols:
        cfg.symbols = args.symbols.split(",")
    feed = csv_bars(args.csv, cfg) if args.csv else synthetic_bars(cfg.symbols, args.days, args.seed, cfg)
    tracker = Tracker(cfg.starting_equity, args.journal or cfg.journal_path, mode="backtest")
    engine = Engine(cfg, PaperBroker(cfg.slippage_bps, cfg.commission_per_share), tracker,
                    log=None if args.quiet else print)
    for group in feed:
        engine.process_bars(group)
    engine.finish()
    print(f"\nBacktest {tracker.run_id}  ({'CSV ' + args.csv if args.csv else f'synthetic data, seed {args.seed}'})")
    print(format_summary(summarize(tracker.trades, cfg.starting_equity)))


def cmd_fetch(args):
    from .alpaca import fetch_to_csv
    cfg = Config.load(args.config)
    tz = ZoneInfo(cfg.timezone)
    start = datetime.fromisoformat(args.start).replace(tzinfo=tz)
    end = datetime.fromisoformat(args.end).replace(hour=23, minute=59, tzinfo=tz)
    n = fetch_to_csv(args.symbols.split(","), start, end, args.out)
    print(f"Wrote {n} bars to {args.out}")


def cmd_live(args):
    from .alpaca import run_live
    run_live(Config.load(args.config), allow_live_money=args.i_understand_this_is_real_money)


def cmd_report(args):
    db = sqlite3.connect(args.journal)
    runs = db.execute("SELECT run_id, mode, started, starting_equity FROM runs ORDER BY started").fetchall()
    if args.run:
        runs = [r for r in runs if r[0] == args.run]
    if not runs:
        print("No runs in journal.")
    for run_id, mode, started, eq in runs[-args.last:]:
        rows = db.execute("SELECT symbol, side, qty, entry_price, exit_price, entry_time, exit_time, pnl, "
                          "r_multiple, exit_reason FROM trades WHERE run_id=?", (run_id,)).fetchall()
        trades = [Trade(r[0], r[1], r[2], r[3], r[4], datetime.fromisoformat(r[5]), datetime.fromisoformat(r[6]),
                        r[7], r[8], r[9]) for r in rows]
        print(f"\n{run_id}  [{mode}]  started {started}  starting equity ${eq:,.2f}")
        print(format_summary(summarize(trades, eq)))
        if args.trades:
            for t in trades:
                print(f"  {t.entry_time:%Y-%m-%d %H:%M}-{t.exit_time:%H:%M} {t.side:5} {t.qty:>5} {t.symbol:<5} "
                      f"{t.entry_price:>9.2f} -> {t.exit_price:>9.2f}  {t.pnl:>+10.2f}  {t.r_multiple:+.2f}R  {t.exit_reason}")


def main():
    p = argparse.ArgumentParser(prog="intraday", description="Intraday trading bot: backtest, paper/live trade, report.")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("backtest", help="Run the strategy over historical or synthetic 1-minute bars")
    b.add_argument("--csv", help="CSV of bars (timestamp,symbol,open,high,low,close,volume)")
    b.add_argument("--days", type=int, default=20, help="synthetic trading days (when no --csv)")
    b.add_argument("--seed", type=int, default=1)
    b.add_argument("--symbols", help="comma-separated, overrides config")
    b.add_argument("--config"); b.add_argument("--journal"); b.add_argument("--quiet", action="store_true")
    b.set_defaults(func=cmd_backtest)

    f = sub.add_parser("fetch", help="Download real 1-minute bars from Alpaca into a CSV")
    f.add_argument("--symbols", required=True); f.add_argument("--start", required=True, help="YYYY-MM-DD")
    f.add_argument("--end", required=True, help="YYYY-MM-DD"); f.add_argument("--out", default="bars.csv")
    f.add_argument("--config")
    f.set_defaults(func=cmd_fetch)

    l = sub.add_parser("live", help="Trade on Alpaca (paper by default) for one session")
    l.add_argument("--config")
    l.add_argument("--i-understand-this-is-real-money", action="store_true")
    l.set_defaults(func=cmd_live)

    r = sub.add_parser("report", help="Summarize runs stored in the journal")
    r.add_argument("--journal", default="journal.sqlite"); r.add_argument("--run")
    r.add_argument("--last", type=int, default=5); r.add_argument("--trades", action="store_true")
    r.set_defaults(func=cmd_report)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
