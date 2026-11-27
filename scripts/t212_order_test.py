"""One-off live order test on the Trading 212 PRACTICE account (refuses to run on live):
buy ~$50 of one stock -> confirm the fill -> place the 12% GTC stop -> confirm it is listed ->
cancel the stop -> sell the shares -> confirm the position is gone.

Usage (only while the US market is open):  python scripts/t212_order_test.py [SYMBOL]
"""
from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from swingbot import calendar_us  # noqa: E402
from swingbot.__main__ import build  # noqa: E402


def main(symbol: str = "MSFT") -> int:
    bot = build()
    b = bot.broker
    if getattr(b, "env", None) != "demo":
        print(f"REFUSING: broker is {getattr(b, 'env', None)!r}, this test only runs on the demo account")
        return 2
    now = datetime.now(timezone.utc)
    sess = bot.session(now.astimezone(calendar_us.NY).date())
    if not sess or not (sess[0] <= now <= sess[1]):
        print("REFUSING: US market is not open right now")
        return 2
    ticker = bot.tickers(now.astimezone(calendar_us.NY).date())[symbol]
    before = b.holdings()
    if ticker in before:
        print(f"REFUSING: the account already holds {ticker}; pick a symbol you don't own")
        return 2
    price = bot.market.live_prices([symbol])[symbol]
    cash0 = b.cash_available()
    print(f"1. Cash available {cash0:.2f}. {symbol} last price {price:.2f}. Buying ${bot.cfg.position_usd:.0f} worth...")
    stop_id = None
    qty = 0.0
    try:
        order = b.market(ticker, bot.cfg.position_usd / price)
        print(f"   order accepted: id {order['id']} quantity {order.get('quantity')} status {order.get('status')}")
        fill = b.wait_fill(order)
        qty = fill.quantity
        print(f"2. FILLED: {fill.quantity} @ {fill.price:.4f} (= ${fill.quantity * fill.price:.2f}); "
              f"slippage vs last price {100 * (fill.price / price - 1):+.3f}%")
        time.sleep(2)
        h = b.holdings().get(ticker)
        print(f"   position now shows: {h}")
        stop_price = round(fill.price * (1 - bot.cfg.stop_pct), 2)
        stop = b.stop(ticker, -qty, stop_price)
        stop_id = stop["id"]
        print(f"3. STOP placed: id {stop_id} at {stop_price} (12% below), good-till-cancelled")
        time.sleep(6)
        listed = [o for o in b.pending_orders() if o.get("id") == stop_id]
        print(f"   stop listed in pending orders: {bool(listed)} {listed[0].get('status') if listed else ''}")
        b.cancel(stop_id)
        stop_id = None
        print("4. Stop cancelled.")
        time.sleep(3)
    finally:
        if stop_id is not None:
            try:
                b.cancel(stop_id)
                print("   (cleanup) stop cancelled")
                time.sleep(3)
            except Exception as e:
                print(f"   (cleanup) could not cancel stop {stop_id}: {e} -- cancel it in the app!")
        if qty:
            for attempt in range(3):
                try:
                    sell = b.market(ticker, -qty)
                    sfill = b.wait_fill(sell)
                    print(f"5. SOLD: {sfill.quantity} @ {sfill.price:.4f}. Round trip P&L "
                          f"${(sfill.price - fill.price) * sfill.quantity:+.4f}")
                    break
                except Exception as e:
                    print(f"   sell attempt {attempt + 1} failed: {e}")
                    time.sleep(4)
            else:
                print(f"!! COULD NOT SELL {qty} {ticker} -- close it in the app")
    time.sleep(2)
    after = b.holdings()
    left = after.get(ticker)
    print(f"6. Position after test: {left if left else 'none (clean)'}; pending orders: "
          f"{[o.get('id') for o in b.pending_orders()]}")
    print(f"   Your own holdings unchanged: {sorted(t for t in before) == sorted(t for t in after if t != ticker)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(*(sys.argv[1:2] or ["MSFT"])))
