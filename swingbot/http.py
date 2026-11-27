"""Tiny HTTP helper (stdlib only, so it runs anywhere incl. Termux) with retries and per-key rate limiting."""
from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request


class HttpError(RuntimeError):
    def __init__(self, status: int, url: str, body: str):
        super().__init__(f"HTTP {status} for {url}: {body[:300]}")
        self.status, self.url, self.body = status, url, body


def basic_auth(user: str, password: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


class Client:
    def __init__(self, base: str, headers: dict[str, str] | None = None, timeout: float = 30):
        self.base = base.rstrip("/")
        self.headers = headers or {}
        self.timeout = timeout
        self._last: dict[str, float] = {}

    def request(self, method: str, path: str, params: dict | None = None, body=None,
                min_interval: float = 0.0, rate_key: str | None = None, retries: int = 4):
        url = self.base + path + ("?" + urllib.parse.urlencode(params) if params else "")
        key = rate_key or path
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Accept": "application/json", **self.headers}
        if data is not None:
            headers["Content-Type"] = "application/json"
        for attempt in range(retries + 1):
            wait = min_interval - (time.monotonic() - self._last.get(key, -1e9))
            if wait > 0:
                time.sleep(wait)
            self._last[key] = time.monotonic()
            req = urllib.request.Request(url, data=data, method=method, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    raw = r.read()
                    return json.loads(raw) if raw else None
            except urllib.error.HTTPError as e:
                text = e.read().decode(errors="replace")
                retryable = e.code in (408, 429, 500, 502, 503, 504)
                # never blindly retry order placement: it is not idempotent at Trading 212
                if retryable and attempt < retries and method == "GET":
                    time.sleep(max(min_interval, 2 ** attempt))
                    continue
                raise HttpError(e.code, url, text) from None
            except (urllib.error.URLError, TimeoutError):
                if attempt < retries and method == "GET":
                    time.sleep(2 ** attempt)
                    continue
                raise
