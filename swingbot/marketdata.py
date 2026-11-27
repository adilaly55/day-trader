"""Prices from Alpaca's free market-data API: daily history (SIP) + live snapshot prices (IEX)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from .http import Client, basic_auth

DATA_URL = "https://data.alpaca.markets"


class MarketData:
    def __init__(self, key_id: str, secret: str, feed_history: str = "sip", feed_live: str = "iex"):
        # Basic auth with key id + secret (in the cloud test environment a proxy injects the real values)
        self.http = Client(DATA_URL, {"Authorization": basic_auth(key_id or "x", secret or "x")})
        self.feed_history, self.feed_live = feed_history, feed_live

    def daily_history(self, symbols: list[str], days: int = 420, end: date | None = None) -> dict[str, list[dict]]:
        """Completed daily bars (oldest first) before today. {symbol: [{date, close, volume}]}
        Daily bars are stamped at midnight New York time, so end=<today 00:00 UTC> excludes today's bar."""
        end = end or datetime.now(timezone.utc).date()
        start = end - timedelta(days=days)
        out: dict[str, list[dict]] = {s: [] for s in symbols}
        for i in range(0, len(symbols), 100):
            params = {"symbols": ",".join(symbols[i:i + 100]), "timeframe": "1Day", "start": start.isoformat() + "T00:00:00Z",
                      "end": end.isoformat() + "T00:00:00Z", "limit": 10000, "adjustment": "all", "feed": self.feed_history}
            while True:
                resp = self.http.request("GET", "/v2/stocks/bars", params, min_interval=0.35, rate_key="data")
                for sym, rows in (resp.get("bars") or {}).items():
                    out.setdefault(sym, []).extend(
                        {"date": r["t"][:10], "close": float(r["c"]), "volume": float(r["v"])} for r in rows)
                if not resp.get("next_page_token"):
                    break
                params["page_token"] = resp["next_page_token"]
        for rows in out.values():
            rows.sort(key=lambda r: r["date"])
        return out

    def live_prices(self, symbols: list[str]) -> dict[str, float]:
        """Latest traded price for each symbol right now."""
        prices: dict[str, float] = {}
        for i in range(0, len(symbols), 100):
            resp = self.http.request("GET", "/v2/stocks/snapshots",
                                     {"symbols": ",".join(symbols[i:i + 100]), "feed": self.feed_live},
                                     min_interval=0.35, rate_key="data")
            for sym, snap in (resp or {}).items():
                trade = (snap or {}).get("latestTrade") or {}
                bar = (snap or {}).get("minuteBar") or {}
                px = trade.get("p") or bar.get("c")
                if px:
                    prices[sym] = float(px)
        return prices
