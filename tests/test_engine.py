import unittest
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from intraday.broker import PaperBroker
from intraday.config import Config
from intraday.data import synthetic_bars
from intraday.engine import Engine
from intraday.models import Bar
from intraday.risk import RiskManager
from intraday.tracker import Tracker

NY = ZoneInfo("America/New_York")
DAY = date(2026, 11, 23)


def bar(minute_of_session, o, h, l, c, sym="TEST", day=DAY):
    ts = datetime.combine(day, datetime.min.time(), NY).replace(hour=9, minute=30) + timedelta(minutes=minute_of_session)
    return Bar(sym, ts, o, h, l, c, 10_000)


def make_engine(cfg=None):
    cfg = cfg or Config(slippage_bps=0)
    tracker = Tracker(cfg.starting_equity)
    return Engine(cfg, PaperBroker(0, 0), tracker, log=None), tracker


def opening_range_then_breakout():
    bars = [bar(m, 100.5, 101.0, 100.0, 100.5) for m in range(15)]   # OR = 100 - 101
    bars.append(bar(15, 100.6, 101.3, 100.6, 101.2))                  # close above OR high and VWAP
    return bars


class TestRisk(unittest.TestCase):
    def test_size_by_risk_and_cap(self):
        r = RiskManager(Config())
        self.assertEqual(r.size(100_000, 100, 95), 100)     # $500 risk / $5
        self.assertEqual(r.size(100_000, 100, 99), 200)     # 500 by risk, capped at 20% notional
        self.assertEqual(r.size(100_000, 100, 100), 0)

    def test_daily_loss_halt(self):
        r = RiskManager(Config())
        r.new_day(100_000)
        self.assertFalse(r.check_daily_loss(98_500))
        self.assertTrue(r.check_daily_loss(97_999))
        self.assertFalse(r.can_open(0))
        r.new_day(97_999)
        self.assertTrue(r.can_open(0))


class TestEngine(unittest.TestCase):
    def run_bars(self, extra):
        engine, tracker = make_engine()
        for b in opening_range_then_breakout() + extra:
            engine.process_bars([b])
        engine.finish()
        return tracker

    def test_long_entry_hits_target(self):
        t = self.run_bars([bar(16, 101.3, 103.0, 101.2, 102.8)])
        self.assertEqual(len(t.trades), 1)
        tr = t.trades[0]
        self.assertEqual((tr.side, tr.exit_reason, tr.entry_price), ("long", "target", 101.2))
        self.assertAlmostEqual(tr.exit_price, 101.2 + 2 * 0.7)
        self.assertAlmostEqual(tr.r_multiple, 2.0, places=2)

    def test_long_entry_hits_stop(self):
        t = self.run_bars([bar(16, 101.1, 101.2, 100.0, 100.2)])
        tr = t.trades[0]
        self.assertEqual((tr.exit_reason, tr.exit_price), ("stop", 100.5))
        self.assertAlmostEqual(tr.r_multiple, -1.0, places=2)

    def test_flattens_before_close(self):
        quiet = [bar(m, 101.2, 101.4, 101.0, 101.2) for m in range(16, 390)]
        t = self.run_bars(quiet)
        self.assertEqual(t.trades[0].exit_reason, "eod_flatten")
        self.assertEqual(t.trades[0].exit_time.strftime("%H:%M"), "15:55")
        self.assertFalse(t.positions)

    def test_one_trade_per_symbol_per_day(self):
        t = self.run_bars([bar(16, 101.1, 101.2, 100.0, 100.2),     # stopped out
                           bar(17, 100.6, 101.3, 100.6, 101.2)])   # breaks out again -> ignored
        self.assertEqual(len(t.trades), 1)

    def test_synthetic_backtest_never_holds_overnight(self):
        cfg = Config()
        engine = Engine(cfg, PaperBroker(2, 0), Tracker(cfg.starting_equity), log=None)
        for g in synthetic_bars(cfg.symbols, 15, 7, cfg):
            engine.process_bars(g)
            self.assertLessEqual(len(engine.tracker.positions), cfg.max_open_positions)
        engine.finish()
        self.assertTrue(engine.tracker.trades)
        for tr in engine.tracker.trades:
            self.assertEqual(tr.entry_time.date(), tr.exit_time.date())
            self.assertLessEqual(tr.exit_time.strftime("%H:%M"), "15:55")


if __name__ == "__main__":
    unittest.main()
