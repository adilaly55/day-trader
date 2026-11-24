"""Download historical bars from Alpaca into data/ (parquet, one file per symbol).

  5-minute bars, regular session 09:30-12:30 ET only (the bot's trading window)
  daily bars (regular session) for context: gaps, trends, average volume, ATR
  pre-market volume per day (04:00-09:30 ET)

Credentials are injected by the environment's network proxy; nothing is read from disk.
Re-running skips symbols already downloaded.
"""
from __future__ import annotations

import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

from universe import ALL

DATA = Path(__file__).resolve().parent.parent / "data"
URL = "https://data.alpaca.markets/v2/stocks/bars"
START, END = "2020-06-01", "2026-11-22"
MODE = "window"            # "window" = 09:30-12:30 bars, "full" = 09:30-16:00 bars, "daily" = daily since 2016
MIN_INTERVAL = 60 / 180          # stay under the free plan's 200 requests/minute
_last = 0.0
_lock = threading.Lock()


def get(params: dict) -> dict:
    global _last
    for attempt in range(6):
        with _lock:                                   # shared rate limit across threads
            wait = MIN_INTERVAL - (time.monotonic() - _last)
            if wait > 0:
                time.sleep(wait)
            _last = time.monotonic()
        try:
            with urllib.request.urlopen(URL + "?" + urllib.parse.urlencode(params), timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 5:
                time.sleep(5 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt < 5:
                time.sleep(5 * (attempt + 1))
                continue
            raise


def bars(symbol: str, timeframe: str, start: str = START, adjustment: str = "split") -> pd.DataFrame:
    params = {"symbols": symbol, "timeframe": timeframe, "start": start, "end": END, "limit": 10000,
              "adjustment": adjustment, "feed": "sip", "sort": "asc"}
    rows = []
    while True:
        resp = get(params)
        rows.extend((resp.get("bars") or {}).get(symbol, []))
        if not resp.get("next_page_token"):
            break
        params["page_token"] = resp["next_page_token"]
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).rename(columns={"t": "ts", "o": "open", "h": "high", "l": "low", "c": "close",
                                            "v": "volume", "vw": "vwap", "n": "trades"})
    df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.tz_convert("America/New_York")
    return df


def main(symbols: list[str]) -> None:
    (DATA / "5min").mkdir(parents=True, exist_ok=True)
    (DATA / "daily").mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(5) as pool:
        list(pool.map(lambda a: one(*a), [(i, s, len(symbols)) for i, s in enumerate(symbols, 1)]))


def one(i: int, sym: str, n: int) -> None:
    try:
        _one(i, sym, n)
    except Exception as e:                            # report and move on; re-run fills gaps
        print(f"[{i}/{n}] {sym}: ERROR {e}", flush=True)


def _one(i: int, sym: str, n: int) -> None:
        if MODE == "daily":
            out = DATA / "daily_long" / f"{sym}.parquet"
            if out.exists():
                return
            out.parent.mkdir(parents=True, exist_ok=True)
            d = bars(sym, "1Day", start="2016-01-01", adjustment="all")   # dividends too: no fake ex-date gaps
            d["date"] = d["ts"].dt.tz_localize(None).dt.normalize()
            d.drop(columns="ts").to_parquet(out, index=False)
            print(f"[{i}/{n}] {sym}: {len(d)} daily bars from {d['date'].iloc[0]:%Y-%m-%d}", flush=True)
            return
        folder = "5min_full" if MODE == "full" else "5min"
        out5 = DATA / folder / f"{sym}.parquet"
        if out5.exists():
            return
        t0 = time.time()
        daily = bars(sym, "1Day")
        intraday = bars(sym, "5Min")
        if intraday.empty or daily.empty:
            print(f"[{i}/{n}] {sym}: NO DATA", flush=True)
            return
        tod = intraday["ts"].dt.hour * 60 + intraday["ts"].dt.minute
        date = intraday["ts"].dt.date
        pre = intraday[(tod >= 240) & (tod < 570)].groupby(date[(tod >= 240) & (tod < 570)])["volume"].sum()
        session = intraday[(tod >= 570) & (tod < (960 if MODE == "full" else 750))].copy()   # bar starts
        daily["date"] = daily["ts"].dt.date
        daily["premarket_volume"] = daily["date"].map(pre).fillna(0)
        if MODE == "window":
            daily.drop(columns="ts").to_parquet(DATA / "daily" / f"{sym}.parquet", index=False)
        out5.parent.mkdir(parents=True, exist_ok=True)
        session.to_parquet(out5, index=False)
        print(f"[{i}/{n}] {sym}: {len(daily)} days, {len(session)} 5-min bars, "
              f"from {session['ts'].iloc[0]:%Y-%m-%d} ({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] in ("--full", "--daily"):
        MODE = args.pop(0)[2:]
    main(args or ALL)
