"""Checkout money, quantity, shipping and code tests. No real DB writes."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from types import SimpleNamespace as Row
import unittest
from unittest.mock import MagicMock, patch

import database
with patch.dict(os.environ, {"FLASK_SECRET_KEY": "isolated-checkout-security-test-key"}):
    import main


class CheckoutCalculationTests(unittest.TestCase):
    def test_quantities_reject_invalid_values(self):
        for value in (0, -1, 1.5, 1.0, True, None, "1.5", "1e2", "abc", "", "-1", 100, "100", "9" * 1000):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    main.checkout_quantities([{"id": 1, "quantity": value}])

    def test_quantities_accept_integers_and_digit_strings(self):
        self.assertEqual(main.checkout_quantities([{"id": 1, "quantity": 2}, {"productId": "2", "quantity": "3"}]), {1: 2, 2: 3})

    def test_repeated_ids_are_aggregated_and_capped(self):
        self.assertEqual(main.checkout_quantities([{"id": 1, "quantity": 2}, {"id": 1, "quantity": 3}]), {1: 5})
        with self.assertRaises(ValueError):
            main.checkout_quantities([{"id": 1, "quantity": 50}, {"id": 1, "quantity": 50}])

    def test_cart_and_product_ids_are_bounded(self):
        for items in ([], {}, [None], [{"id": 1, "quantity": 1}] * 101, [{"id": True, "quantity": 1}], [{"id": 1.5, "quantity": 1}], [{"id": 2**31, "quantity": 1}]):
            with self.assertRaises(ValueError):
                main.checkout_quantities(items)

    def test_decimal_total_uses_only_database_price(self):
        rows = {1: Row(Price=Decimal("0.10")), 2: Row(Price=Decimal("0.20"))}
        self.assertEqual(main.checkout_total(rows, {1: 3, 2: 1}), Decimal("0.50"))
        self.assertIsInstance(main.checkout_total(rows, {1: 3}), Decimal)

    def test_invalid_catalog_prices(self):
        for price in ("NaN", "Infinity", "-1", "0"):
            with self.assertRaises(ValueError):
                main.checkout_total({1: Row(Price=price)}, {1: 1})

    def test_total_capacity(self):
        with self.assertRaises(ValueError):
            main.checkout_total({value: Row(Price=Decimal("9999999999999999.99")) for value in (1, 2)}, {1: 99, 2: 99})

    def test_shipping_tier_boundaries(self):
        for distance, fee in ((0, 10000), (2, 10000), (2.00001, 15000), (5, 15000), (5.00001, 25000), (10, 25000), (10.00001, 50000)):
            self.assertEqual(main.checkout_shipping_fee(distance), Decimal(fee))
        for invalid in (float("nan"), float("inf"), -1):
            with self.assertRaises(ValueError):
                main.checkout_shipping_fee(invalid)

    def test_invalid_coordinates(self):
        for lat, lon in ((True, 1), (1, False), (91, 0), (0, -181), ("NaN", 1), ("Infinity", 1), ("invalid", 1)):
            with self.assertRaises(ValueError):
                main.shipping_fee_for_coordinates(lat, lon)

    @unittest.skipUnless(shutil.which("node"), "Node unavailable for frontend parity check")
    def test_shipping_matches_existing_frontend(self):
        source = Path("static/js/checkout.js").read_text(encoding="utf-8-sig")
        self.assertRegex(source, r"const SHOP_LAT\s*=\s*21\.0338;")
        self.assertRegex(source, r"const SHOP_LNG\s*=\s*105\.8019;")
        functions = source[source.index("function calculateDistance("):source.index("function calculateShipping(")]
        points = [(21.0338, 105.8019), (21.04, 105.81), (21.06, 105.84), (21.10, 105.88), (10, 106)]
        script = functions + "\nconsole.log(JSON.stringify(" + json.dumps(points) + ".map(([lat,lon])=>calculateShippingFee(calculateDistance(21.0338,105.8019,lat,lon)))));"
        output = subprocess.run([shutil.which("node"), "-e", script], capture_output=True, text=True, check=True)
        self.assertEqual([int(main.shipping_fee_for_coordinates(*point)) for point in points], json.loads(output.stdout))

    def test_order_codes_are_unique_under_parallel_generation(self):
        with ThreadPoolExecutor(max_workers=8) as executor:
            codes = list(executor.map(lambda _: main.generate_order_code(), range(10000)))
        self.assertEqual(len(set(codes)), 10000)
        self.assertTrue(all(re.fullmatch(r"BCV[A-Z2-7]{17}", code) for code in codes))

    def test_unique_error_classification(self):
        postgres = RuntimeError("fixture")
        postgres.sqlstate = "23505"
        self.assertTrue(main.is_unique_violation(postgres))
        for native in (2601, 2627):
            self.assertTrue(main.is_unique_violation(RuntimeError("23000", f"fixture ({native})")))
        self.assertFalse(main.is_unique_violation(RuntimeError("23000", "foreign key fixture (547)")))
        self.assertFalse(main.is_unique_violation(RuntimeError("fixture")))


class OrderCodeRouteTests(unittest.TestCase):
    def setUp(self):
        self.connection = MagicMock()
        self.cursor = self.connection.cursor.return_value
        self.cursor.fetchall.return_value = [Row(ProductID=987654, IsActive=True, IsAvailable=True)]
        self.data = {"customerName": "Fixture", "phone": "0900000000", "email": "fixture@example.com", "address": "Fixture", "latitude": 21.0338, "longitude": 105.8019, "products": [{"id": 987654, "quantity": 1, "price": 100}], "shippingFee": 0, "paymentMethod": "CASH"}
        for replacement in (patch.dict(main.app.config, TESTING=True, SECRET_KEY="isolated-checkout-route-key"), patch.object(main, "get_connection", return_value=self.connection)):
            replacement.start()
            self.addCleanup(replacement.stop)
        self.client = main.app.test_client()

    def authorize(self):
        with self.client.session_transaction() as saved:
            saved["customer_id"] = 987654
            saved["checkout_verified_email"] = "fixture@example.com"
            saved["checkout_verified_email_at"] = int(time.time())

    def test_many_requests_have_distinct_codes_on_each_backend(self):
        codes = set()
        for mode in ("local", "postgres"):
            with patch.dict(os.environ, {"DB_MODE": mode}):
                for _ in range(50):
                    self.authorize()
                    response = self.client.post("/api/orders", json=self.data)
                    self.assertEqual(response.status_code, 200)
                    code = response.json["orderCode"]
                    self.assertNotIn(code, codes)
                    self.assertRegex(code, r"^BCV[A-Z2-7]{17}$")
                    codes.add(code)

    def test_unique_errors_rollback_and_keep_otp(self):
        postgres = RuntimeError("sensitive-fixture-error")
        postgres.sqlstate = "23505"
        errors = [("postgres", postgres), ("local", RuntimeError("23000", "sensitive-fixture-error (2627)")), ("local", RuntimeError("23000", "sensitive-fixture-error (2601)"))]
        for mode, error in errors:
            with self.subTest(mode=mode), patch.dict(os.environ, {"DB_MODE": mode}):
                self.connection.reset_mock()
                self.cursor.execute.side_effect = [None, error]
                self.authorize()
                response = self.client.post("/api/orders", json=self.data)
                self.assertEqual(response.status_code, 409)
                self.assertNotIn("sensitive-fixture-error", response.get_data(as_text=True))
                self.connection.rollback.assert_called_once()
                self.connection.commit.assert_not_called()
                self.connection.close.assert_called_once()
                with self.client.session_transaction() as saved:
                    self.assertIn("checkout_verified_email", saved)


if __name__ == "__main__":
    unittest.main()
