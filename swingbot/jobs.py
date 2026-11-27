"""The bot's daily routine. `tick()` is called every few minutes (by cron on the phone) and decides
what, if anything, to do right now:

  * shortly after the US open  -> BUY the stocks flagged the evening before
  * shortly before the US close -> SELL recovered/expired positions, then SCAN for tomorrow's buys

Times come from the exchange schedule, so US daylight-saving changes, holidays and early closes
are handled automatically. Each job runs at most once per day.
"""
from __future__ import annotations

import time
from datetime import date, datetime, timedelta, timezone
from typing import Callable

from . import calendar_us, strategy
from .broker import BrokerError
from .config import Config
from .state import State


class Bot:
    def __init__(self, cfg: Config, broker, market, earnings, state: State, notify: Callable,
                 now_fn: Callable[[], datetime] | None = None):
        self.cfg, self.broker, self.market, self.earnings = cfg, broker, market, earnings
        self.state, self.notify = state, notify
        self.now_fn = now_fn or (lambda: datetime.now(timezone.utc))

    # ------------------------------------------------------------------ scheduling
    def session(self, day: date):
        try:
            s = self.broker.us_session(day.isoformat())
            if s:
                return s
        except Exception as e:                              # fall back to the built-in calendar
            self.state.log("warn", f"exchange schedule unavailable: {e}")
        return calendar_us.session(day)

    def tick(self) -> str:
        now = self.now_fn()
        today = now.astimezone(calendar_us.NY).date()
        sess = self.session(today)
        if not sess:
            return "market closed today"
        open_, close = sess
        done = self.state.data["done"]
        b0, b1 = self.cfg.buy_window_min
        s0, s1 = self.cfg.sell_window_min
        if open_ + timedelta(minutes=b0) <= now <= open_ + timedelta(minutes=b1) and done.get("buy") != today.isoformat():
            self.buy_job(today)
            return "ran buy job"
        if close - timedelta(minutes=s0) <= now <= close - timedelta(minutes=s1) and done.get("sell") != today.isoformat():
            self.sell_job(today)
            return "ran sell job"
        return "nothing to do now"

    # ------------------------------------------------------------------ helpers
    def tickers(self, today: date) -> dict[str, str]:
        st = self.state.data
        if st.get("tickers_date") != today.isoformat() or not st.get("tickers"):
            st["tickers"] = self.broker.us_ticker_map(self.cfg.universe)
            st["tickers_date"] = today.isoformat()
            self.state.save()
        return st["tickers"]

    def _days_held(self, history: list[dict], entry: str, today: date) -> int:
        return sum(1 for r in history if r["date"] > entry) + (1 if today.isoformat() > entry else 0)

    def _sell(self, sym: str, pos: dict, today: date, reason: str, price_hint: float | None = None) -> None:
        if pos.get("stop_order_id") is not None:
            try:
                self.broker.cancel(pos["stop_order_id"])
            except Exception as e:
                self.state.log("warn", f"{sym}: could not cancel stop order: {e}")
        last_err = None
        for _ in range(3):                                   # the cancelled stop may take a moment to free the shares
            try:
                order = self.broker.market(pos["ticker"], -pos["quantity"])
                fill = self.broker.wait_fill(order)
                break
            except BrokerError as e:
                last_err = e
                time.sleep(3)
        else:
            self.notify("SELL FAILED", f"{sym}: {last_err}. Check the Trading 212 app.", important=True)
            self.state.log("error", f"sell {sym} failed: {last_err}")
            return
        days = pos.get("_days", 0)
        res = self.state.record_trade(sym, pos, today.isoformat(), fill.price, days, reason, self.broker.env)
        self.state.positions.pop(sym, None)
        self.state.save()
        self.notify(f"SOLD {sym} {res['ret']:+.2f}%",
                    f"{pos['quantity']} @ {fill.price:.2f} (bought {pos['entry_price']:.2f}), "
                    f"P&L ${res['pnl']:+.2f}. {reason}")

    def _reconcile(self, today: date, prices: dict[str, float]) -> None:
        """Positions the bot thinks it holds but the broker no longer has = stop hit (or sold by hand)."""
        if hasattr(self.broker, "check_stops"):              # dry-run simulates the broker-side stops
            self.broker.check_stops(prices)
        holdings = self.broker.holdings()
        for sym, pos in list(self.state.positions.items()):
            h = holdings.get(pos["ticker"])
            if h is None or h.quantity < pos["quantity"] * 0.5:
                px = pos.get("stop_price") or prices.get(sym) or pos["entry_price"]
                res = self.state.record_trade(sym, pos, today.isoformat(), px, 0,
                                              "stop hit or closed outside the bot (price approximate)", self.broker.env)
                self.state.positions.pop(sym)
                self.state.save()
                self.notify(f"{sym} position gone", f"Stop hit or sold manually. Approx {res['ret']:+.1f}%.",
                            important=True)

    # ------------------------------------------------------------------ jobs
    def sell_job(self, today: date) -> None:
        cfg = self.cfg
        tickers = self.tickers(today)
        held = list(self.state.positions)
        symbols = sorted(set(cfg.universe) | set(held))
        prices = self.market.live_prices(symbols)
        self._reconcile(today, prices)
        history = self.market.daily_history(symbols)

        # 1) exits
        for sym, pos in list(self.state.positions.items()):
            px = prices.get(sym)
            if px is None:
                self.notify("No price", f"{sym}: no live price, keeping position today", important=True)
                continue
            days = self._days_held(history.get(sym, []), pos["entry_date"], today)
            reason = strategy.exit_reason(cfg, history.get(sym, []), px, days)
            if reason:
                pos["_days"] = days
                self._sell(sym, pos, today, reason, px)

        # 2) scan for tomorrow
        free = cfg.max_positions - len(self.state.positions)
        picks: list[strategy.Candidate] = []
        skipped_earnings: list[str] = []
        if free > 0 and not self.state.data["paused"]:
            cands = []
            for sym in cfg.universe:
                if sym in self.state.positions or sym not in tickers or sym not in prices:
                    continue
                c = strategy.entry_signal(cfg, sym, history.get(sym, []), prices[sym])
                if c:
                    cands.append(c)
            if cands:
                try:
                    reporting = self.earnings.reporting_within(cfg.earnings_buffer_days, today)
                except Exception as e:
                    reporting = None
                    self.notify("Earnings check failed", f"{e}. No new buys tomorrow, to be safe.", important=True)
                if reporting is None:
                    cands = []
                else:
                    skipped_earnings = [c.symbol for c in cands if c.symbol in reporting]
                    cands = [c for c in cands if c.symbol not in reporting]
            picks = strategy.rank(cands)[: free + 2]             # a couple of spares in case a buy fails
        self.state.data["pending"] = {"made": today.isoformat(), "symbols": [c.symbol for c in picks],
                                      "details": [c.__dict__ for c in picks]}
        self.state.data["done"]["sell"] = today.isoformat()
        self.state.save()
        msg = (f"Holding {len(self.state.positions)}/{cfg.max_positions}. "
               + (f"Tomorrow's buys: {', '.join(f'{c.symbol} (RSI {c.rsi})' for c in picks[:free])}"
                  if picks else "No buy signals for tomorrow.")
               + (f" Skipped (earnings): {', '.join(skipped_earnings)}." if skipped_earnings else "")
               + (" [PAUSED: no new buys]" if self.state.data["paused"] else ""))
        self.notify("Evening check done", msg)
        self.state.log("sell_job", msg)

    def buy_job(self, today: date) -> None:
        cfg = self.cfg
        st = self.state.data
        st["done"]["buy"] = today.isoformat()
        self.state.save()
        pending = st.get("pending") or {}
        made = pending.get("made")
        if st["paused"] or not pending.get("symbols") or not made or made >= today.isoformat() or \
                (today - date.fromisoformat(made)).days > 5:
            st["pending"] = None
            self.state.save()
            return
        tickers = self.tickers(today)
        prices = self.market.live_prices(pending["symbols"])
        self._reconcile(today, prices)
        bought = []
        for sym in pending["symbols"]:
            if len(self.state.positions) >= cfg.max_positions:
                break
            if sym in self.state.positions or sym not in tickers or sym not in prices:
                continue
            try:
                if self.broker.cash_available() < cfg.position_usd * 1.02:
                    self.notify("Not enough cash", f"Skipping {sym}: less than ${cfg.position_usd} available", important=True)
                    break
                qty = cfg.position_usd / prices[sym]
                order = self.broker.market(tickers[sym], qty)
                fill = self.broker.wait_fill(order)
            except Exception as e:
                self.notify("BUY FAILED", f"{sym}: {e}", important=True)
                self.state.log("error", f"buy {sym} failed: {e}")
                continue
            pos = {"ticker": tickers[sym], "quantity": fill.quantity, "entry_price": fill.price,
                   "entry_date": today.isoformat(), "stop_price": round(fill.price * (1 - cfg.stop_pct), 2),
                   "stop_order_id": None}
            self.state.positions[sym] = pos
            self.state.save()
            try:
                stop = self.broker.stop(tickers[sym], -fill.quantity, pos["stop_price"])
                pos["stop_order_id"] = stop["id"]
                self.state.save()
            except Exception as e:
                self.notify("STOP ORDER FAILED", f"{sym}: {e}. Position has no disaster stop!", important=True)
            bought.append(f"{sym} {fill.quantity} @ {fill.price:.2f}")
        st["pending"] = None
        self.state.save()
        if bought:
            self.notify("Bought", "; ".join(bought) + f". Stops {int(cfg.stop_pct*100)}% below.")
        self.state.log("buy_job", f"bought: {bought}")

    # ------------------------------------------------------------------ manual commands
    def close_all(self, today: date) -> None:
        for sym, pos in list(self.state.positions.items()):
            pos["_days"] = 0
            self._sell(sym, pos, today, "closed manually (close-all)")
        self.state.data["paused"] = True
        self.state.data["pending"] = None
        self.state.save()
        self.notify("All positions closed", "Bot paused. Run `resume` to restart.", important=True)

    def status(self) -> str:
        lines = [f"Broker: {self.broker.env}   Paused: {self.state.data['paused']}"]
        pos = self.state.positions
        if pos:
            prices = self.market.live_prices(list(pos))
            lines.append("Open positions:")
            for sym, p in pos.items():
                px = prices.get(sym, p["entry_price"])
                lines.append(f"  {sym:6} {p['quantity']:>8} bought {p['entry_date']} @ {p['entry_price']:.2f}  "
                             f"now {px:.2f} ({(px / p['entry_price'] - 1) * 100:+.2f}%)  stop {p['stop_price']}")
        else:
            lines.append("No open positions.")
        pend = self.state.data.get("pending")
        if pend and pend.get("symbols"):
            lines.append(f"Queued for next open (from {pend['made']}): {', '.join(pend['symbols'])}")
        trades = self.state.trades()
        if trades:
            pnl = sum(t[5] for t in trades)
            wins = sum(1 for t in trades if t[5] > 0)
            avg = sum(t[6] for t in trades) / len(trades)
            lines.append(f"Closed trades: {len(trades)}, wins {wins} ({100 * wins / len(trades):.0f}%), "
                         f"avg {avg:+.2f}%, total P&L ${pnl:+.2f}")
            for t in trades[-10:]:
                lines.append(f"  {t[0]:6} {t[1]} -> {t[2]}  {t[3]:.2f} -> {t[4]:.2f}  {t[6]:+.2f}%  ({t[8]})")
        return "\n".join(lines)
