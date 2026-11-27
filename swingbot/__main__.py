"""Command line:  python -m swingbot <command>

  tick       run whatever is due right now (cron calls this every 5 minutes)
  status     open positions, queued buys, results so far
  check      test all connections without trading
  buy-now    force the morning buy job now (testing)
  sell-now   force the evening sell + scan job now (testing)
  pause      stop opening new positions (existing ones are still managed)
  resume     undo pause
  close-all  sell everything the bot holds now and pause
"""
from __future__ import annotations

import fcntl
import sys
from datetime import datetime, timezone

from . import calendar_us
from .broker import DryRun, Trading212
from .config import HOME, Config, load_secrets
from .earnings import Earnings
from .jobs import Bot
from .marketdata import MarketData
from .notify import Notifier
from .state import State


def build(cfg: Config | None = None) -> Bot:
    cfg = cfg or Config.load()
    sec = load_secrets()
    HOME.mkdir(parents=True, exist_ok=True)
    market = MarketData(sec.get("ALPACA_KEY_ID", ""), sec.get("ALPACA_SECRET_KEY", ""),
                        cfg.alpaca_feed_history, cfg.alpaca_feed_live)
    if cfg.broker == "t212":
        broker = Trading212(sec.get("T212_API_KEY", ""), sec.get("T212_API_SECRET", ""), cfg.t212_env, cfg.qty_decimals)
    else:
        broker = DryRun(HOME / "dryrun_broker.json", market.live_prices)
    return Bot(cfg, broker, market, Earnings(sec.get("FINNHUB_TOKEN", "")), State(HOME),
               Notifier(HOME, cfg.notify_termux, cfg.ntfy_topic))


def check(bot: Bot) -> None:
    today = datetime.now(timezone.utc).astimezone(calendar_us.NY).date()
    print(f"Broker mode: {bot.broker.env}   data folder: {HOME}")
    try:
        p = bot.market.live_prices(["AAPL", "MSFT"])
        print(f"[ok] Alpaca prices: {p}")
    except Exception as e:
        print(f"[FAIL] Alpaca: {e}")
    try:
        n = len(bot.earnings.reporting_within(7, today))
        print(f"[ok] Finnhub earnings calendar: {n} companies report in the next 7 days")
    except Exception as e:
        print(f"[FAIL] Finnhub: {e}")
    if bot.broker.env != "dryrun":
        try:
            acct = bot.broker.account()
            print(f"[ok] Trading 212 ({bot.broker.env}): account {acct.get('id')}, currency {acct.get('currency')}, "
                  f"cash available {acct['cash']['availableToTrade']}")
            m = bot.tickers(today)
            missing = sorted(set(bot.cfg.universe) - set(m))
            print(f"[ok] {len(m)}/{len(bot.cfg.universe)} stocks tradable on Trading 212"
                  + (f" (missing: {', '.join(missing)})" if missing else ""))
        except Exception as e:
            print(f"[FAIL] Trading 212: {e}")
    s = bot.session(today)
    if s:
        print(f"[ok] US market today: {s[0].astimezone(calendar_us.NY):%H:%M}-{s[1].astimezone(calendar_us.NY):%H:%M} New York"
              f" = {s[0].astimezone(DUBAI):%H:%M}-{s[1].astimezone(DUBAI):%H:%M} Dubai")
    else:
        print("[ok] US market closed today")


from zoneinfo import ZoneInfo  # noqa: E402
DUBAI = ZoneInfo("Asia/Dubai")


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd = argv[0]
    HOME.mkdir(parents=True, exist_ok=True)
    lock = open(HOME / ".lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)     # never run two copies at once
    except BlockingIOError:
        print("another swingbot run is in progress")
        return 0
    bot = build()
    today = datetime.now(timezone.utc).astimezone(calendar_us.NY).date()
    try:
        if cmd == "tick":
            print(bot.tick())
        elif cmd == "status":
            print(bot.status())
        elif cmd == "check":
            check(bot)
        elif cmd == "buy-now":
            bot.buy_job(today)
        elif cmd == "sell-now":
            bot.sell_job(today)
        elif cmd == "pause":
            bot.state.data["paused"] = True; bot.state.save(); print("paused: no new positions")
        elif cmd == "resume":
            bot.state.data["paused"] = False; bot.state.save(); print("resumed")
        elif cmd == "close-all":
            bot.close_all(today)
        else:
            print(f"unknown command {cmd!r}\n{__doc__}")
            return 2
    except Exception as e:
        bot.notify("swingbot error", f"{cmd}: {e}", important=True)
        raise
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
