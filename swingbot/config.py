"""Settings. Override any field in ~/.swingbot/config.json (see config.example.json)."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

HOME = Path(os.environ.get("SWINGBOT_HOME", Path.home() / ".swingbot"))

# 2016 S&P 100 members still listed (the list the strategy was tested on; WBA was taken private in 2025).
UNIVERSE = [
    "AAPL", "ABBV", "ABT", "ACN", "AIG", "ALL", "AMGN", "AMZN", "AXP", "BA", "BAC", "BIIB", "BK", "BLK",
    "BMY", "BRK.B", "C", "CAT", "CL", "CMCSA", "COF", "COP", "COST", "CSCO", "CVS", "CVX", "DHR", "DIS",
    "DUK", "EMR", "EXC", "F", "META", "FDX", "GD", "GE", "GILD", "GM", "GOOGL", "GS", "HAL", "HD", "HON",
    "IBM", "INTC", "JNJ", "JPM", "KHC", "KMI", "KO", "LLY", "LMT", "LOW", "MA", "MCD", "MDLZ", "MDT", "MET",
    "MMM", "MO", "MRK", "MS", "MSFT", "NEE", "NKE", "ORCL", "OXY", "BKNG", "PEP", "PFE", "PG", "PM", "PYPL",
    "QCOM", "SBUX", "SLB", "SO", "SPG", "T", "TGT", "TXN", "UNH", "UNP", "UPS", "USB", "V", "VZ",
    "WFC", "WMT", "XOM",
]


@dataclass
class Config:
    # --- strategy (validated in research/RESULTS_SWING.md, Tests C and D) ---
    universe: list[str] = field(default_factory=lambda: list(UNIVERSE))
    rsi_period: int = 2
    rsi_max: float = 20.0              # buy when RSI(2) is below this...
    trend_sma: int = 200               # ...and the price is above its 200-day average
    exit_sma: int = 5                  # sell when the price closes back above its 5-day average
    max_hold_days: int = 5             # or after 5 trading days
    stop_pct: float = 0.12             # disaster stop held at the broker, 12% below the fill price
    min_dollar_volume: float = 2e7     # 20-day average traded value
    earnings_buffer_days: int = 8      # skip a stock if it reports earnings within this many calendar days

    # --- money ---
    position_usd: float = 50.0
    max_positions: int = 5

    # --- timing, relative to the US session (handles DST, holidays and early closes) ---
    buy_window_min: tuple = (0, 20)    # buy between open+0 and open+20 minutes
    sell_window_min: tuple = (16, 4)   # decide/sell between close-16 and close-4 minutes

    # --- connections ---
    broker: str = "dryrun"             # "dryrun" (simulated, no orders) or "t212"
    t212_env: str = "demo"             # "demo" or "live" (live needs allow_live_money=true too)
    allow_live_money: bool = False
    qty_decimals: int = 3              # fractional share precision tried first (falls back automatically)
    alpaca_feed_history: str = "sip"
    alpaca_feed_live: str = "iex"      # free plan: real-time IEX prices
    notify_termux: bool = True         # Android notifications via Termux:API
    ntfy_topic: str = ""               # optional push notifications via ntfy.sh (any device)

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        path = path or HOME / "config.json"
        cfg = cls()
        if path.exists():
            data = json.loads(path.read_text())
            known = {f.name for f in fields(cls)}
            bad = set(data) - known
            if bad:
                raise ValueError(f"Unknown settings in {path}: {sorted(bad)}")
            for k, v in data.items():
                setattr(cfg, k, tuple(v) if isinstance(getattr(cfg, k), tuple) else v)
        if cfg.t212_env == "live" and not cfg.allow_live_money:
            raise ValueError("t212_env is 'live' but allow_live_money is false. Refusing to trade real money.")
        return cfg

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


def load_secrets(path: Path | None = None) -> dict[str, str]:
    """KEY=VALUE lines from ~/.swingbot/secrets.env (never committed). Environment variables win."""
    path = path or HOME / "secrets.env"
    out: dict[str, str] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("ALPACA_KEY_ID", "ALPACA_SECRET_KEY", "T212_API_KEY", "T212_API_SECRET", "FINNHUB_TOKEN"):
        if os.environ.get(k):
            out[k] = os.environ[k]
    return out
