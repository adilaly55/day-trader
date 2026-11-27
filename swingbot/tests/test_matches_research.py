"""The live bot's signal code must reproduce the research backtest's signals on real data.
Skipped if the research data folder hasn't been downloaded."""
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "daily_long"
sys.path.insert(0, str(ROOT / "research"))


@unittest.skipUnless(DATA.exists(), "research data not downloaded")
class TestMatchesResearch(unittest.TestCase):
    def test_entry_and_exit_signals_identical(self):
        import swing as sw
        from swingbot import strategy
        from swingbot.config import Config
        cfg = Config()
        syms = sw.load()
        checked = mismatches = signals = 0
        for name in ["AAPL", "JPM", "XOM", "INTC", "KO", "BA"]:
            s = syms[name]
            I = s.ind
            with np.errstate(invalid="ignore"):
                ref = (s.C > I["sma200"]) & (I["rsi2"] < 20) & (I["dollar_vol"] > 2e7) & np.isfinite(I["sma200"])
            hist = [{"date": str(d), "close": float(c), "volume": float(v)} for d, c, v in zip(s.dates, s.C, s.V)]
            for i in range(260, len(s.C)):
                got = strategy.entry_signal(cfg, name, hist[i - 300 if i > 300 else 0:i], float(s.C[i])) is not None
                # research dollar volume includes the signal day; the bot uses the 20 completed days before it
                if bool(ref[i]) != got:
                    dv_prev = np.mean(s.C[i - 20:i] * s.V[i - 20:i])
                    if not (abs(dv_prev - 2e7) / 2e7 < 0.5):
                        mismatches += 1
                signals += got
                checked += 1
                ex_ref = s.C[i] > I["sma5"][i]
                ex_got = strategy.exit_reason(cfg, hist[i - 10:i], float(s.C[i]), 0) is not None
                self.assertEqual(bool(ex_ref), ex_got)
        self.assertGreater(signals, 100)
        self.assertEqual(mismatches, 0, f"{mismatches} of {checked} days differ")


if __name__ == "__main__":
    unittest.main()
