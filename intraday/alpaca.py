"""Alpaca (https://alpaca.markets) connection: market data, order routing, and the live loop.

Uses only the standard library. Credentials come from the environment:
    APCA_API_KEY_ID, APCA_API_SECRET_KEY
    APCA_API_BASE_URL  (optional; defaults to the PAPER endpoint)
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .broker import Broker
from .config import Config
from .data import group_by_ts
from .engine import Engine
from .models import Bar, Fill
from .tracker import Tracker, format_summary, summarize

PAPER_URL = "https://paper-api.alpaca.markets"
DATA_URL = "https://data.alpaca.markets"


class AlpacaError(RuntimeError):
    pass


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class AlpacaClient:
    def __init__(self, feed: str = "iex"):
        self.key = os.environ.get("APCA_API_KEY_ID")
        self.secret = os.environ.get("APCA_API_SECRET_KEY")
        if not self.key or not self.secret:
            raise AlpacaError("Set APCA_API_KEY_ID and APCA_API_SECRET_KEY (free paper account at alpaca.markets).")
        self.base_url = os.environ.get("APCA_API_BASE_URL", PAPER_URL).rstrip("/")
        self.feed = feed

    @property
    def is_paper(self) -> bool:
        return "paper-api" in self.base_url

    def _request(self, method: str, url: str, params: dict | None = None, body: dict | None = None):
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode() if body is not None else None
        headers = {"APCA-API-KEY-ID": self.key, "APCA-API-SECRET-KEY": self.secret,
                   "Content-Type": "application/json"}
        for attempt in range(4):
            req = urllib.request.Request(url, data=data, method=method, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=15) as r:
                    raw = r.read()
                    return json.loads(raw) if raw else None
            except urllib.error.HTTPError as e:
                if (e.code == 429 or e.code >= 500) and attempt < 3:
                    time.sleep(2 ** attempt)
                    continue
                raise AlpacaError(f"{method} {url} -> {e.code}: {e.read().decode(errors='replace')}") from e
            except urllib.error.URLError:
                if attempt < 3:
                    time.sleep(2 ** attempt)
                    continue
                raise

    # trading API
    def account(self):   return self._request("GET", f"{self.base_url}/v2/account")
    def clock(self):     return self._request("GET", f"{self.base_url}/v2/clock")
    def positions(self): return self._request("GET", f"{self.base_url}/v2/positions")
    def get_order(self, order_id): return self._request("GET", f"{self.base_url}/v2/orders/{order_id}")

    def submit_market_order(self, symbol: str, qty: int, side: str):
        return self._request("POST", f"{self.base_url}/v2/orders", body={
            "symbol": symbol, "qty": str(qty), "side": side, "type": "market",
            "time_in_force": "day", "client_order_id": f"intraday-{uuid.uuid4().hex[:16]}"})

    # market data API
    def bars(self, symbols: list[str], start: datetime, end: datetime | None = None) -> list[Bar]:
        params = {"symbols": ",".join(symbols), "timeframe": "1Min", "start": _iso(start),
                  "limit": 10000, "feed": self.feed, "adjustment": "raw", "sort": "asc"}
        if end:
            params["end"] = _iso(end)
        out: list[Bar] = []
        while True:
            resp = self._request("GET", f"{DATA_URL}/v2/stocks/bars", params=params)
            for sym, rows in (resp.get("bars") or {}).items():
                for r in rows:
                    ts = datetime.fromisoformat(r["t"].replace("Z", "+00:00"))
                    out.append(Bar(sym, ts, r["o"], r["h"], r["l"], r["c"], r["v"]))
            token = resp.get("next_page_token")
            if not token:
                return out
            params["page_token"] = token


class AlpacaBroker(Broker):
    def __init__(self, client: AlpacaClient, fill_timeout: float = 30.0):
        self.client = client
        self.fill_timeout = fill_timeout

    def market_order(self, symbol, side, qty, ref_price, ts):
        order = self.client.submit_market_order(symbol, qty, side)
        deadline = time.monotonic() + self.fill_timeout
        while True:
            status = order["status"]
            if status == "filled":
                return Fill(float(order["filled_avg_price"]), int(float(order["filled_qty"])), 0.0)
            if status in ("canceled", "rejected", "expired"):
                raise AlpacaError(f"Order {order['id']} for {symbol} {status}")
            if time.monotonic() > deadline:
                raise AlpacaError(f"Order {order['id']} for {symbol} not filled after {self.fill_timeout}s")
            time.sleep(0.5)
            order = self.client.get_order(order["id"])


def fetch_to_csv(symbols: list[str], start: datetime, end: datetime, out_path: str) -> int:
    import csv
    bars = AlpacaClient().bars(symbols, start, end)
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "symbol", "open", "high", "low", "close", "volume"])
        for b in sorted(bars, key=lambda b: (b.ts, b.symbol)):
            w.writerow([b.ts.isoformat(), b.symbol, b.open, b.high, b.low, b.close, b.volume])
    return len(bars)


def run_live(cfg: Config, allow_live_money: bool = False) -> None:
    client = AlpacaClient()
    if not client.is_paper and not allow_live_money:
        raise SystemExit(f"APCA_API_BASE_URL={client.base_url} is a REAL-MONEY endpoint. "
                         "Re-run with --i-understand-this-is-real-money if you really mean it.")
    if client.positions():
        raise SystemExit("Account already has open positions. Close them first so the bot's tracking is accurate.")

    tz = ZoneInfo(cfg.timezone)
    clock = client.clock()
    if not clock["is_open"]:
        nxt = datetime.fromisoformat(clock["next_open"].replace("Z", "+00:00"))
        print(f"Market closed. Waiting for next open at {nxt.astimezone(tz):%a %Y-%m-%d %H:%M %Z}...")
        while datetime.now(timezone.utc) < nxt:
            time.sleep(min(60, max(1, (nxt - datetime.now(timezone.utc)).total_seconds())))

    equity = float(client.account()["equity"])
    tracker = Tracker(equity, cfg.journal_path, mode="paper" if client.is_paper else "LIVE")
    engine = Engine(cfg, AlpacaBroker(client), tracker)
    print(f"[{tracker.run_id}] equity ${equity:,.2f}  symbols {cfg.symbols}  ({'PAPER' if client.is_paper else 'LIVE'})")

    def completed_bars(since: datetime) -> list[Bar]:
        now = datetime.now(timezone.utc)
        return [b for b in client.bars(cfg.symbols, since) if b.ts + timedelta(minutes=1) <= now]

    # Catch up on today's bars so the opening range / VWAP are correct if started late
    session_open = datetime.combine(datetime.now(tz).date(), cfg.market_open, tz)
    last_seen = session_open - timedelta(minutes=1)
    history = completed_bars(session_open)
    for group in group_by_ts(history):
        engine.warmup(group)
        last_seen = group[0].ts
    if history:
        print(f"Warmed up on {len(history)} bars from today's session.")

    while True:
        now = datetime.now(timezone.utc)
        time.sleep(60 - now.second - now.microsecond / 1e6 + 5)     # 5s after each minute closes
        local_now = datetime.now(tz)
        try:
            new = [b for b in completed_bars(last_seen + timedelta(minutes=1)) if b.ts > last_seen]
            for group in group_by_ts(new):
                engine.process_bars(group)
                last_seen = group[0].ts
        except Exception as e:                                       # keep running; open positions are retried next bar
            print(f"{local_now:%H:%M:%S} ERROR: {e}")
        if local_now.time() >= cfg.flatten_at and not tracker.positions:
            break
        if local_now.time() >= cfg.market_close:
            break

    engine.finish()
    print(format_summary(summarize(tracker.trades, equity)))
