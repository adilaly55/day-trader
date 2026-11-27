import json
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from swingbot import calendar_us, strategy
from swingbot.broker import DryRun
from swingbot.config import Config
from swingbot.indicators import rsi, sma
from swingbot.jobs import Bot
from swingbot.state import State

NY = calendar_us.NY


def hist(closes, start=date(2025, 1, 1), vol=1e6):
    out, d = [], start
    for c in closes:
        while d.weekday() >= 5:
            d += timedelta(days=1)
        out.append({"date": d.isoformat(), "close": float(c), "volume": vol})
        d += timedelta(days=1)
    return out


class FakeMarket:
    def __init__(self):
        self.prices, self.history = {}, {}

    def live_prices(self, symbols):
        return {s: self.prices[s] for s in symbols if s in self.prices}

    def daily_history(self, symbols, days=420, end=None):
        return {s: list(self.history.get(s, [])) for s in symbols}


class FakeEarnings:
    def __init__(self, reporting=()):
        self.reporting = set(reporting)

    def reporting_within(self, days, today=None):
        return set(self.reporting)


class TestIndicators(unittest.TestCase):
    def test_match_pandas_research_implementation(self):
        import random
        import pandas as pd
        import numpy as np
        rng = random.Random(1)
        xs = [100.0]
        for _ in range(300):
            xs.append(xs[-1] * (1 + rng.gauss(0, 0.02)))
        s = pd.Series(xs)
        diff = s.diff()
        up = diff.clip(lower=0).ewm(alpha=1 / 2, adjust=False).mean()
        dn = (-diff.clip(upper=0)).ewm(alpha=1 / 2, adjust=False).mean()
        ref = (100 - 100 / (1 + up / dn)).iloc[-1]
        self.assertAlmostEqual(rsi(xs, 2), ref, places=6)
        self.assertAlmostEqual(rsi(xs[-60:], 2), ref, places=3)     # bot uses the last 60 closes
        self.assertAlmostEqual(sma(xs, 200), float(np.mean(xs[-200:])), places=9)


class TestStrategy(unittest.TestCase):
    def setUp(self):
        self.cfg = Config()

    def test_entry_on_dip_in_uptrend(self):
        closes = [100 + i * 0.2 for i in range(250)] + [148, 146]      # long uptrend, then 2 down days
        c = strategy.entry_signal(self.cfg, "X", hist(closes, vol=1e6), 144.0)
        self.assertIsNotNone(c)
        self.assertLess(c.rsi, 20)

    def test_no_entry_in_downtrend_or_illiquid(self):
        down = [200 - i * 0.2 for i in range(250)] + [149, 148]
        self.assertIsNone(strategy.entry_signal(self.cfg, "X", hist(down), 146.0))
        up = [100 + i * 0.2 for i in range(250)] + [148, 146]
        self.assertIsNone(strategy.entry_signal(self.cfg, "X", hist(up, vol=10), 144.0))   # $20M liquidity rule

    def test_exit_rules(self):
        h = hist([100, 101, 102, 103, 104])
        self.assertIn("recovered", strategy.exit_reason(self.cfg, h, 110.0, 1))
        self.assertIsNone(strategy.exit_reason(self.cfg, h, 95.0, 2))
        self.assertIn("time limit", strategy.exit_reason(self.cfg, h, 95.0, 5))


class TestBotFlow(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.cfg = Config(universe=["AAA", "BBB"], position_usd=50, max_positions=5)
        self.market = FakeMarket()
        up = [100 + i * 0.2 for i in range(250)] + [148, 146]
        self.market.history = {"AAA": hist(up), "BBB": hist(up)}
        self.market.prices = {"AAA": 144.0, "BBB": 151.0}             # AAA dipped, BBB did not
        self.now = datetime(2026, 12, 1, 20, 50, tzinfo=timezone.utc)  # Tue 15:50 New York
        self.notes = []
        self.bot = self.make_bot()

    def make_bot(self, earnings=()):
        broker = DryRun(self.tmp / "broker.json", self.market.live_prices)
        return Bot(self.cfg, broker, self.market, FakeEarnings(earnings), State(self.tmp),
                   lambda t, m, important=False: self.notes.append((t, m)), now_fn=lambda: self.now)

    def test_full_cycle(self):
        self.assertEqual(self.bot.tick(), "ran sell job")
        self.assertEqual(self.bot.state.data["pending"]["symbols"], ["AAA"])
        self.assertEqual(self.bot.tick(), "nothing to do now")                 # once per day
        # next morning, 09:35 New York
        self.now = datetime(2026, 12, 2, 14, 35, tzinfo=timezone.utc)
        self.assertEqual(self.bot.tick(), "ran buy job")
        pos = self.bot.state.positions["AAA"]
        self.assertAlmostEqual(pos["quantity"] * pos["entry_price"], 50, delta=0.2)
        self.assertAlmostEqual(pos["stop_price"], round(144.0 * 0.88, 2))
        self.assertIsNotNone(pos["stop_order_id"])
        # same evening: price recovers above the 5-day average -> sell
        self.market.prices["AAA"] = 150.0
        self.now = datetime(2026, 12, 2, 20, 50, tzinfo=timezone.utc)
        self.assertEqual(self.bot.tick(), "ran sell job")
        self.assertNotIn("AAA", self.bot.state.positions)
        trades = self.bot.state.trades()
        self.assertEqual(len(trades), 1)
        self.assertGreater(trades[0][5], 0)
        self.assertEqual(json.loads((self.tmp / "broker.json").read_text())["stops"], {})   # stop cancelled

    def test_earnings_filter_and_pause(self):
        bot = self.make_bot(earnings=["AAA"])
        bot.sell_job(date(2026, 12, 1))
        self.assertEqual(bot.state.data["pending"]["symbols"], [])
        bot.state.data["paused"] = True
        bot = self.make_bot()
        bot.state.data["paused"] = True
        bot.sell_job(date(2026, 12, 1))
        self.assertEqual(bot.state.data["pending"]["symbols"], [])

    def test_stop_hit_is_reconciled(self):
        self.bot.sell_job(date(2026, 12, 1))
        self.bot.buy_job(date(2026, 12, 2))
        self.market.prices["AAA"] = 120.0                         # below the 12% stop
        self.bot.sell_job(date(2026, 12, 3))
        self.assertNotIn("AAA", self.bot.state.positions)
        self.assertIn("stop", self.bot.state.trades()[0][8])

    def test_stale_or_same_day_queue_is_not_bought(self):
        self.bot.state.data["pending"] = {"made": "2026-11-20", "symbols": ["AAA"]}
        self.bot.buy_job(date(2026, 12, 2))
        self.assertEqual(self.bot.state.positions, {})

    def test_time_exit_after_5_days(self):
        self.bot.sell_job(date(2026, 12, 1))
        self.bot.buy_job(date(2026, 12, 2))
        self.market.prices["AAA"] = 140.0                         # never recovers, stays above the stop
        self.bot.sell_job(date(2026, 12, 8))                      # Wed 2 Dec -> Tue 8 Dec
        self.assertIn("AAA", self.bot.state.positions)            # 4 trading days: keep
        self.bot.state.data["done"] = {}
        for d in ("2026-12-02", "2026-12-03", "2026-12-04", "2026-12-07", "2026-12-08"):
            self.market.history["AAA"].append({"date": d, "close": 140.0, "volume": 1e6})
        self.bot.sell_job(date(2026, 12, 9))                      # 5th trading day after entry
        self.assertNotIn("AAA", self.bot.state.positions)
        self.assertIn("time limit", self.bot.state.trades()[0][8])


class TestSchedule(unittest.TestCase):
    def test_dst_and_early_close(self):
        # winter: open 14:30 UTC = 18:30 Dubai; summer: 13:30 UTC = 17:30 Dubai
        o, c = calendar_us.session(date(2026, 12, 1))
        self.assertEqual((o.astimezone(timezone.utc).hour, c.astimezone(timezone.utc).hour), (14, 21))
        o, c = calendar_us.session(date(2026, 7, 1))
        self.assertEqual((o.astimezone(timezone.utc).hour, c.astimezone(timezone.utc).hour), (13, 20))
        self.assertEqual(calendar_us.session(date(2026, 11, 27))[1].hour, 13)    # day after Thanksgiving
        self.assertIsNone(calendar_us.session(date(2026, 12, 25)))
        self.assertIsNone(calendar_us.session(date(2026, 11, 28)))               # Saturday


if __name__ == "__main__":
    unittest.main()
