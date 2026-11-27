"""Broker connections: Trading 212 (demo or live) and a dry-run simulator with the same interface."""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .calendar_us import NY
from .http import Client, HttpError, basic_auth

T212_URLS = {"demo": "https://demo.trading212.com", "live": "https://live.trading212.com"}


@dataclass
class Holding:
    ticker: str            # broker ticker, e.g. AAPL_US_EQ
    quantity: float
    avg_price: float
    current_price: float


@dataclass
class Fill:
    order_id: int
    price: float
    quantity: float


class BrokerError(RuntimeError):
    pass


class Trading212:
    """Trading 212 public API v0 (Invest account). Rate limits per the official docs."""

    def __init__(self, api_key: str, api_secret: str, env: str = "demo", qty_decimals: int = 3):
        if env not in T212_URLS:
            raise ValueError(env)
        self.env = env
        self.http = Client(T212_URLS[env] + "/api/v0", {"Authorization": basic_auth(api_key or "x", api_secret or "x")})
        self.qty_decimals = qty_decimals

    # ---- reads
    def account(self) -> dict:
        return self.http.request("GET", "/equity/account/summary", min_interval=5.1)

    def cash_available(self) -> float:
        return float(self.account()["cash"]["availableToTrade"])

    def holdings(self) -> dict[str, Holding]:
        rows = self.http.request("GET", "/equity/positions", min_interval=1.1)
        out = {}
        for r in rows or []:
            t = r["instrument"]["ticker"]
            out[t] = Holding(t, float(r["quantity"]), float(r["averagePricePaid"]), float(r["currentPrice"]))
        return out

    def pending_orders(self) -> list[dict]:
        return self.http.request("GET", "/equity/orders", min_interval=5.1) or []

    def instruments(self) -> list[dict]:
        return self.http.request("GET", "/equity/metadata/instruments", min_interval=51)

    def exchanges(self) -> list[dict]:
        return self.http.request("GET", "/equity/metadata/exchanges", min_interval=31)

    # ---- orders
    def _qty(self, q: float, decimals: int) -> float:
        f = 10 ** decimals
        return math.floor(abs(q) * f) / f * (1 if q > 0 else -1)

    def _place(self, path: str, body: dict, min_interval: float) -> dict:
        """Try the configured precision, then fewer decimals if Trading 212 rejects the quantity."""
        last: Exception | None = None
        for dec in range(self.qty_decimals, -1, -1):
            q = self._qty(body["quantity"], dec)
            if q == 0:
                break
            try:
                return self.http.request("POST", path, body={**body, "quantity": q}, min_interval=min_interval)
            except HttpError as e:
                last = e
                if e.status == 400 and ("quantity" in e.body.lower() or "precision" in e.body.lower()):
                    continue
                raise BrokerError(str(e)) from None
        raise BrokerError(f"order rejected: {last}")

    def market(self, ticker: str, quantity: float) -> dict:
        """Positive quantity buys, negative sells."""
        return self._place("/equity/orders/market", {"ticker": ticker, "quantity": quantity, "extendedHours": False}, 1.3)

    def stop(self, ticker: str, quantity: float, stop_price: float) -> dict:
        return self._place("/equity/orders/stop", {"ticker": ticker, "quantity": quantity,
                                                   "stopPrice": round(stop_price, 2),
                                                   "timeValidity": "GOOD_TILL_CANCEL"}, 2.1)

    def cancel(self, order_id: int) -> None:
        try:
            self.http.request("DELETE", f"/equity/orders/{order_id}", min_interval=1.1)
        except HttpError as e:
            if e.status != 404:          # already gone (filled/cancelled) is fine
                raise

    def wait_fill(self, order: dict, timeout: float = 90) -> Fill:
        """Market orders leave the pending list once filled; then read the fill from order history."""
        oid, ticker = order["id"], order.get("ticker") or order["instrument"]["ticker"]
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                o = self.http.request("GET", f"/equity/orders/{oid}", min_interval=1.1)
                if o.get("status") in ("CANCELLED", "REJECTED"):
                    raise BrokerError(f"order {oid} {o['status']}")
            except HttpError as e:
                if e.status != 404:
                    raise
                hist = self.http.request("GET", "/equity/history/orders", {"ticker": ticker, "limit": 10},
                                         min_interval=3.1, rate_key="history")
                for item in (hist or {}).get("items", []):
                    if item["order"]["id"] == oid and item.get("fill"):
                        f = item["fill"]
                        return Fill(oid, float(f["price"]), abs(float(f["quantity"])))
            time.sleep(2)
        raise BrokerError(f"order {oid} not confirmed filled within {timeout}s - check the app")

    # ---- helpers
    def us_ticker_map(self, symbols: list[str]) -> dict[str, str]:
        """Map plain symbols (AAPL, BRK.B) to Trading 212 tickers for USD-traded US stocks."""
        want = {s.upper(): s for s in symbols}
        by_ticker = {s.upper().replace(".", "_") + "_US_EQ": s for s in symbols}
        out: dict[str, str] = {}
        for ins in self.instruments():
            if ins.get("type") != "STOCK" or ins.get("currencyCode") != "USD":
                continue
            if ins["ticker"] in by_ticker:                       # e.g. BK_US_EQ, now shown as "BNY"
                out[by_ticker[ins["ticker"]]] = ins["ticker"]
                continue
            short = (ins.get("shortName") or "").upper()
            for cand in (short, short.replace("_", "."), short.replace("/", ".")):
                if cand in want and want[cand] not in out:
                    out[want[cand]] = ins["ticker"]
        return out

    def us_session(self, day_iso: str, ref_ticker: str = "AAPL_US_EQ") -> tuple[datetime, datetime] | None:
        """Today's regular-session open/close (UTC) from Trading 212's exchange schedule, or None if closed."""
        sched_id = next((i["workingScheduleId"] for i in self.instruments() if i["ticker"] == ref_ticker), None)
        for ex in self.exchanges():
            for ws in ex.get("workingSchedules", []):
                if ws.get("id") != sched_id:
                    continue
                opens, closes = [], []
                for ev in ws.get("timeEvents", []):
                    ts = datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    if ts.astimezone(NY).date().isoformat() != day_iso:
                        continue
                    if ev["type"] == "OPEN":
                        opens.append(ts)
                    elif ev["type"] == "CLOSE":
                        closes.append(ts)
                if opens and closes:
                    return min(opens), max(closes)
                return None
        return None


class DryRun:
    """Simulated broker: no orders leave the phone. Holdings persist in a JSON file."""

    env = "dryrun"

    def __init__(self, path: Path, prices_fn, cash: float = 10_000.0):
        self.path, self.prices_fn = path, prices_fn
        self.data = json.loads(path.read_text()) if path.exists() else {"cash": cash, "holdings": {}, "stops": {}, "next_id": 1}

    def _save(self):
        self.path.write_text(json.dumps(self.data, indent=1))

    def cash_available(self) -> float:
        return self.data["cash"]

    def holdings(self) -> dict[str, Holding]:
        out = {}
        for t, h in self.data["holdings"].items():
            out[t] = Holding(t, h["quantity"], h["avg_price"], h.get("current_price", h["avg_price"]))
        return out

    def _sym(self, ticker: str) -> str:
        return ticker.replace("_US_EQ", "").replace("_", ".")

    def market(self, ticker: str, quantity: float) -> dict:
        px = self.prices_fn([self._sym(ticker)]).get(self._sym(ticker))
        if not px:
            raise BrokerError(f"no price for {ticker}")
        oid = self.data["next_id"]; self.data["next_id"] += 1
        q = round(quantity, 3)
        h = self.data["holdings"].get(ticker)
        if q > 0:
            self.data["cash"] -= q * px
            self.data["holdings"][ticker] = {"quantity": q, "avg_price": px, "current_price": px}
        else:
            self.data["cash"] += -q * px
            self.data["holdings"].pop(ticker, None)
        self._save()
        return {"id": oid, "ticker": ticker, "_fill": px, "_qty": abs(q), "status": "FILLED"}

    def stop(self, ticker: str, quantity: float, stop_price: float) -> dict:
        oid = self.data["next_id"]; self.data["next_id"] += 1
        self.data["stops"][str(oid)] = {"ticker": ticker, "quantity": quantity, "stop": stop_price}
        self._save()
        return {"id": oid}

    def cancel(self, order_id: int) -> None:
        self.data["stops"].pop(str(order_id), None)
        self._save()

    def wait_fill(self, order: dict, timeout: float = 0) -> Fill:
        return Fill(order["id"], order["_fill"], order["_qty"])

    def check_stops(self, prices: dict[str, float]) -> list[tuple[str, float]]:
        """Simulate stop orders against current prices. Returns [(ticker, fill_price)]."""
        hit = []
        for oid, s in list(self.data["stops"].items()):
            px = prices.get(self._sym(s["ticker"]))
            if px is not None and px <= s["stop"] and s["ticker"] in self.data["holdings"]:
                h = self.data["holdings"].pop(s["ticker"])
                self.data["cash"] += h["quantity"] * px
                self.data["stops"].pop(oid)
                hit.append((s["ticker"], px))
        self._save()
        return hit

    def us_ticker_map(self, symbols: list[str]) -> dict[str, str]:
        return {s: s.replace(".", "_") + "_US_EQ" for s in symbols}

    def us_session(self, day_iso: str, ref_ticker: str = "") -> None:
        return None            # use the built-in calendar
