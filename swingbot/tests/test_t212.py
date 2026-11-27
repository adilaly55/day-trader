"""Trading212 client against simulated responses shaped like the official API reference."""
import unittest

from swingbot.broker import Trading212
from swingbot.http import HttpError


class FakeHttp:
    def __init__(self):
        self.calls = []
        self.pending = {}
        self.history = []
        self.next_id = 100
        self.reject_decimals_above = None

    def request(self, method, path, params=None, body=None, min_interval=0.0, rate_key=None, retries=4):
        self.calls.append((method, path, body))
        if path == "/equity/metadata/instruments":
            return [{"ticker": "AAPL_US_EQ", "shortName": "AAPL", "type": "STOCK", "currencyCode": "USD", "workingScheduleId": 7},
                    {"ticker": "BRK_B_US_EQ", "shortName": "BRK.B", "type": "STOCK", "currencyCode": "USD", "workingScheduleId": 7},
                    {"ticker": "BK_US_EQ", "shortName": "BNY", "type": "STOCK", "currencyCode": "USD", "workingScheduleId": 7},
                    {"ticker": "AAPLl_EQ", "shortName": "AAPL", "type": "STOCK", "currencyCode": "GBX", "workingScheduleId": 9},
                    {"ticker": "SPY4l_EQ", "shortName": "SPY4", "type": "ETF", "currencyCode": "USD", "workingScheduleId": 9}]
        if path == "/equity/metadata/exchanges":
            return [{"id": 1, "name": "NYSE", "workingSchedules": [{"id": 7, "timeEvents": [
                {"date": "2026-12-01T09:00:00.000Z", "type": "PRE_MARKET_OPEN"},
                {"date": "2026-12-01T14:30:00.000Z", "type": "OPEN"},
                {"date": "2026-12-01T21:00:00.000Z", "type": "CLOSE"},
                {"date": "2026-12-02T14:30:00.000Z", "type": "OPEN"}]}]}]
        if path == "/equity/orders/market":
            q = body["quantity"]
            if self.reject_decimals_above is not None and len(str(abs(q)).split(".")[-1]) > self.reject_decimals_above:
                raise HttpError(400, path, '{"code":"InvalidQuantity","message":"quantity precision mismatch"}')
            oid = self.next_id; self.next_id += 1
            self.history.append({"order": {"id": oid, "ticker": body["ticker"]},
                                 "fill": {"price": 200.5, "quantity": q}})
            return {"id": oid, "ticker": body["ticker"], "status": "NEW", "quantity": q}
        if path.startswith("/equity/orders/") and method == "GET":
            raise HttpError(404, path, "not found")                # filled -> no longer pending
        if path == "/equity/history/orders":
            return {"items": [h for h in self.history if h["order"]["ticker"] == params["ticker"]][::-1]}
        if path == "/equity/orders/stop":
            oid = self.next_id; self.next_id += 1
            return {"id": oid, "stopPrice": body["stopPrice"]}
        if path == "/equity/positions":
            return [{"instrument": {"ticker": "AAPL_US_EQ"}, "quantity": 0.249, "averagePricePaid": 200.5, "currentPrice": 201}]
        raise AssertionError(path)


class TestT212(unittest.TestCase):
    def setUp(self):
        self.b = Trading212("k", "s", "demo", qty_decimals=3)
        self.b.http = FakeHttp()

    def test_ticker_map_prefers_usd_us_listing(self):
        m = self.b.us_ticker_map(["AAPL", "BRK.B", "MSFT", "BK"])
        self.assertEqual(m, {"AAPL": "AAPL_US_EQ", "BRK.B": "BRK_B_US_EQ", "BK": "BK_US_EQ"})

    def test_session_from_schedule(self):
        o, c = self.b.us_session("2026-12-01")
        self.assertEqual((o.hour, c.hour), (14, 21))
        self.assertIsNone(self.b.us_session("2026-12-05"))

    def test_buy_fill_and_stop(self):
        order = self.b.market("AAPL_US_EQ", 50 / 200.0)
        self.assertEqual(self.b.http.calls[-1][2]["quantity"], 0.25)
        fill = self.b.wait_fill(order, timeout=5)
        self.assertEqual((fill.price, fill.quantity), (200.5, 0.25))
        self.b.stop("AAPL_US_EQ", -fill.quantity, 176.444)
        body = self.b.http.calls[-1][2]
        self.assertEqual((body["quantity"], body["stopPrice"], body["timeValidity"]), (-0.25, 176.44, "GOOD_TILL_CANCEL"))

    def test_precision_fallback(self):
        self.b.http.reject_decimals_above = 1
        self.b.market("AAPL_US_EQ", 0.2777)
        qs = [c[2]["quantity"] for c in self.b.http.calls if c[1] == "/equity/orders/market"]
        self.assertEqual(qs, [0.277, 0.27, 0.2])

    def test_sell_rounds_down_never_oversells(self):
        self.b.market("AAPL_US_EQ", -0.24999)
        self.assertEqual(self.b.http.calls[-1][2]["quantity"], -0.249)

    def test_holdings(self):
        h = self.b.holdings()["AAPL_US_EQ"]
        self.assertEqual((h.quantity, h.avg_price), (0.249, 200.5))


if __name__ == "__main__":
    unittest.main()
