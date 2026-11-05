"""Phases 2G-I: mocked mutations, real OTP hooks, optional SELECT-only SQL checks."""

import ast
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import os
import re
from pathlib import Path
import sys
import time
from threading import Event, Lock
from types import SimpleNamespace as Row
import unittest
from unittest.mock import MagicMock, patch

# Load .env before the temporary app-secret override is restored.
import database

# Import the real app without creating a secret-key file or logging credentials.
with patch.dict(os.environ, {"FLASK_SECRET_KEY": "isolated-order-flow-test-key"}), patch("builtins.print"):
    import main
from routes import admin_orders, shipper


SELECT_CATALOG = {"local": {}, "postgres": {}}


class OrderChecks:
    def setUp(self):
        config = patch.dict(main.app.config, TESTING=True, SECRET_KEY="isolated-order-flow-test-key")
        config.start()
        self.addCleanup(config.stop)
        self.client = main.app.test_client()
        self.connection = MagicMock()
        self.cursor = self.connection.cursor.return_value
        self.cursor.rowcount = 1
        self.cursor.fetchone.return_value = None
        self.cursor.fetchall.return_value = []
        self.renderers = {}
        for module in (main, admin_orders, shipper):
            replacement = patch.object(module, "get_connection", return_value=self.connection)
            replacement.start()
            self.addCleanup(replacement.stop)
            render = patch.object(module, "render_template", return_value="page")
            self.renderers[module] = render.start()
            self.addCleanup(render.stop)
        env = patch.dict(os.environ, {"DB_MODE": self.mode})
        env.start()
        self.addCleanup(env.stop)
        self.cursor.execute.side_effect = self.record_sql
        self.checkout = {"customerName": "Fixture", "phone": "0900000000", "email": "fixture@example.com",
                         "address": "Fixture address", "latitude": 10, "longitude": 106,
                         "products": [{"id": 987654, "price": 100, "quantity": 2}],
                         "shippingFee": 20, "paymentMethod": "CASH"}

    def record_sql(self, query, params=()):
        self.assertEqual(query.count("%s" if self.mode == "postgres" else "?"), len(params))
        if self.mode == "postgres":
            self.assertNotIn("?", query)
            self.assertNotIn("N'", query)
            self.assertNotIn("ISNULL", query)
            self.assertNotIn("GETDATE", query)
        if query.lstrip().upper().startswith("SELECT"):
            SELECT_CATALOG[self.mode][(query, tuple(params))] = None

    def role(self, role):
        with self.client.session_transaction() as session:
            session.clear()
            session.update(role=role, user_id=987654, fullname="Fixture", shipper_session_token="fixture-token")

    def customer(self, verified=True):
        with self.client.session_transaction() as session:
            session.clear()
            session["customer_id"] = 987654
            if verified:
                session["checkout_verified_email"] = "fixture@example.com"
                session["checkout_verified_email_at"] = int(time.time())

    def shipper_row(self, working=True, active=True, token="fixture-token"):
        return (active, working, token)

    def assert_locked(self, index, table):
        sql = self.cursor.execute.call_args_list[index].args[0]
        if self.mode == "postgres":
            self.assertIn(f'"{table}"', sql)
            self.assertIn("FOR UPDATE", sql)
        else:
            self.assertIn("UPDLOCK", sql)
            self.assertIn("HOLDLOCK", sql)

    def test_admin_order_filters(self):
        self.role("Admin")
        for filters, expected in (({}, ()), ({"date": "2026-01-02", "status": "Đã tiếp nhận"}, ("2026-01-02", "Đã tiếp nhận")), ({"month": "2026-01", "status": "x' OR 1=1 --"}, (2026, 1, "x' OR 1=1 --")), ({"month": "invalid"}, ()), ({"month": "2026-13"}, ())):
            self.cursor.reset_mock()
            self.assertEqual(self.client.get("/admin/orders", query_string=filters).status_code, 200)
            args = self.cursor.execute.call_args_list[0].args
            self.assertEqual(args[1:], (expected,) if expected else ())
            self.assertNotIn("x' OR 1=1 --", args[0])
            self.assertEqual(self.cursor.execute.call_count, 2)

    def test_admin_grouped_orders(self):
        self.role("Admin")
        order = Row(CreatedAt=datetime(2026, 1, 2))
        self.cursor.fetchall.side_effect = [[order], []]
        self.client.get("/admin/orders")
        self.assertEqual(self.renderers[admin_orders].call_args.kwargs["grouped_orders"], {order.CreatedAt.date(): [order]})

    def test_admin_confirm_payment_branches(self):
        self.role("Admin")
        for row, status, commits in ((None, 404, 0), (Row(PaymentMethod="CASH", PaymentStatus=""), 400, 0), (Row(PaymentMethod="BANK_TRANSFER", PaymentStatus="Đã thanh toán"), 200, 0), (Row(PaymentMethod="BANK_TRANSFER", PaymentStatus="Chờ khách chuyển khoản"), 409, 0), (Row(PaymentMethod="BANK_TRANSFER", PaymentStatus="Khách báo đã chuyển khoản"), 200, 1)):
            self.connection.reset_mock()
            self.cursor.fetchone.return_value = row
            response = self.client.post("/admin/orders/987654/confirm-payment")
            self.assertEqual(response.status_code, status)
            self.assert_locked(0, "Orders")
            self.assertEqual(self.connection.commit.call_count, commits)
            self.assertEqual(self.connection.rollback.call_count, 0 if commits else 1)

    def test_admin_assign_locks_and_checks(self):
        self.role("Admin")
        active = Row(UserID=987654, FullName="Fixture", IsActive=True, IsWorking=True)
        for driver, order, expected in ((None, None, 404), (Row(**{**vars(active), "IsActive": False}), None, 400), (Row(**{**vars(active), "IsWorking": False}), None, 400), (active, None, 404), (active, Row(Status="Hoàn thành", DriverID=None), 400), (active, Row(Status="Đang giao", DriverID=1), 400), (active, Row(Status="Đã giao shipper", DriverID=987654), 200), (active, Row(Status="Đã tiếp nhận", DriverID=None), 200)):
            self.connection.reset_mock()
            self.cursor.fetchone.side_effect = [driver, order]
            self.assertEqual(self.client.post("/admin/orders/assign", json={"orderId": 987654, "driverId": 987654}).status_code, expected)
            self.assert_locked(0, "Users")
            if self.cursor.execute.call_count >= 2:
                self.assert_locked(1, "Orders")
        self.connection.commit.assert_called_once()

    def test_admin_status(self):
        self.role("Admin")
        for current, requested, expected in (("Đã tiếp nhận", "Đang chuẩn bị", 200), ("Đã tiếp nhận", "Đã hủy", 200), ("Đang giao", "Đã hủy", 400), ("Hoàn thành", "Đang chuẩn bị", 400), ("Đã tiếp nhận", "invalid", 400)):
            self.connection.reset_mock()
            self.cursor.fetchone.return_value = Row(Status=current, DriverID=None)
            self.assertEqual(self.client.post("/admin/orders/update/987654", json={"status": requested}).status_code, expected)
            if requested != "invalid":
                self.assert_locked(0, "Orders")

    def test_admin_permissions(self):
        self.role("Shipper")
        self.assertEqual(self.client.get("/admin/orders").status_code, 302)
        for endpoint in ("assign", "update/987654", "987654/confirm-payment"):
            self.assertEqual(self.client.post(f"/admin/orders/{endpoint}", json={}).status_code, 403)
        self.connection.cursor.assert_not_called()

    def test_admin_payment_failure_rollback(self):
        self.role("Admin")
        self.cursor.fetchone.return_value = Row(PaymentMethod="BANK_TRANSFER", PaymentStatus="Khách báo đã chuyển khoản")
        self.cursor.execute.side_effect = [None, RuntimeError("fixture")]
        with patch("builtins.print"):
            self.assertEqual(self.client.post("/admin/orders/987654/confirm-payment").status_code, 500)
        self.connection.rollback.assert_called_once()

    def test_shipper_sessions(self):
        for row, expected in ((None, "SESSION_INVALID"), (self.shipper_row(active=False), "SHIPPER_LOCKED"), (self.shipper_row(token="other-token"), "SESSION_CONFLICT"), (self.shipper_row(token=""), "SESSION_INVALID"), (self.shipper_row(), "OK")):
            self.role("Shipper")
            self.cursor.fetchone.return_value = row
            response = self.client.get("/shipper/session-status")
            self.assertEqual(response.json["code"], expected)
            self.assertEqual(response.status_code, 200 if expected == "OK" else 401)
        self.role("Admin")
        self.assertEqual(self.client.get("/shipper/session-status").status_code, 401)

    def test_shipper_page_queries_and_range(self):
        self.role("Shipper")
        self.cursor.fetchone.side_effect = [self.shipper_row(), (True, True), (3, 1, 2), (1,), (1, 120), (0,)]
        response = self.client.get("/shipper/orders", query_string={"from_date": "2026-01-31", "to_date": "2026-01-01"})
        self.assertEqual(response.status_code, 200)
        context = self.renderers[shipper].call_args.kwargs
        self.assertEqual((context["from_date"], context["to_date"]), ("2026-01-01", "2026-01-31"))
        self.assertEqual((context["total_done"], context["today_done"], context["month_done"]), (3, 1, 2))
        self.assertEqual(self.cursor.execute.call_count, 8)

    def test_toggle_work(self):
        for working, count, status in ((False, 0, 200), (True, 0, 200), (True, 2, 400)):
            self.role("Shipper")
            self.connection.reset_mock()
            self.cursor.fetchone.side_effect = [self.shipper_row(working=working), (count,)]
            response = self.client.post("/shipper/toggle-work")
            self.assertEqual(response.status_code, status)
            self.assert_locked(0, "Users")
            if status == 200:
                self.assertEqual(response.json["working"], 0 if working else 1)
                self.assertIsInstance(self.cursor.execute.call_args.args[1][0], bool)
                self.connection.commit.assert_called_once()
            else:
                self.connection.rollback.assert_called_once()

    def test_shipper_transitions(self):
        for old, new in (("Đã giao shipper", "Đang chuẩn bị"), ("Đang chuẩn bị", "Đang giao"), ("Đang giao", "Hoàn thành")):
            self.role("Shipper")
            self.connection.reset_mock()
            self.cursor.fetchone.side_effect = [self.shipper_row(), (old,)]
            response = self.client.post("/shipper/update/987654", json={"status": new})
            self.assertEqual(response.status_code, 200)
            self.assert_locked(0, "Users")
            self.assert_locked(1, "Orders")
            self.connection.commit.assert_called_once()

    def test_shipper_rejects_stale_or_unowned_order(self):
        for row, new, rowcount, expected in ((None, "Đang giao", 1, 404), (("Hoàn thành",), "Đang giao", 1, 400), (("Đã giao shipper",), "Hoàn thành", 1, 400), (("Đang chuẩn bị",), "Đang giao", 0, 409)):
            self.role("Shipper")
            self.connection.reset_mock()
            self.cursor.fetchone.side_effect = [self.shipper_row(), row]
            self.cursor.rowcount = rowcount
            self.assertEqual(self.client.post("/shipper/update/987654", json={"status": new}).status_code, expected)
            self.connection.rollback.assert_called_once()
            self.connection.commit.assert_not_called()

    def test_shipper_cancel(self):
        self.role("Shipper")
        self.cursor.fetchone.side_effect = [self.shipper_row(), ("Đang giao", "Old note")]
        response = self.client.post("/shipper/cancel/987654", json={"reason": "Fixture reason", "note": "Fixture note"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Old note | Không giao được: Fixture reason", self.cursor.execute.call_args.args[1][0])
        self.assert_locked(1, "Orders")
        self.connection.commit.assert_called_once()

    def test_cancel_validation_and_conflict(self):
        self.role("Shipper")
        self.assertEqual(self.client.post("/shipper/cancel/987654", json={}).status_code, 400)
        for row, count, expected in ((None, 1, 404), (("Đang chuẩn bị", ""), 1, 400), (("Đang giao", ""), 0, 409)):
            self.connection.reset_mock()
            self.cursor.fetchone.side_effect = [self.shipper_row(), row]
            self.cursor.rowcount = count
            self.assertEqual(self.client.post("/shipper/cancel/987654", json={"reason": "Fixture"}).status_code, expected)
            self.connection.rollback.assert_called_once()

    def test_gps_session_and_working(self):
        for row, expected in ((self.shipper_row(), 200), (self.shipper_row(working=False), 400), (self.shipper_row(token="old"), 401)):
            self.role("Shipper")
            self.connection.reset_mock()
            self.cursor.fetchone.return_value = row
            self.assertEqual(self.client.post("/shipper/location", json={"latitude": 10, "longitude": 106}).status_code, expected)
            self.assert_locked(0, "Users")
            if expected == 200:
                self.assertEqual(self.cursor.execute.call_args.args[1], (987654, 10.0, 106.0))
                self.connection.commit.assert_called_once()
            else:
                self.assertEqual(self.cursor.execute.call_count, 1)
                self.connection.rollback.assert_called_once()

    def test_gps_invalid(self):
        for data in ({}, {"latitude": "nan", "longitude": 1}, {"latitude": 91, "longitude": 1}, {"latitude": 1, "longitude": 181}):
            self.assertEqual(self.client.post("/shipper/location", json=data).status_code, 400)
        self.connection.cursor.assert_not_called()

    def test_shipper_write_error_closes_connection(self):
        self.role("Shipper")
        self.cursor.fetchone.return_value = self.shipper_row()
        self.cursor.execute.side_effect = [None, RuntimeError("fixture")]
        with self.assertRaises(RuntimeError):
            self.client.post("/shipper/location", json={"latitude": 10, "longitude": 106})
        self.connection.close.assert_called_once()
        self.connection.commit.assert_not_called()

    def test_staff_login_and_logout(self):
        for role in ("Admin", "Shipper"):
            self.connection.reset_mock()
            self.cursor.fetchone.return_value = Row(UserID=987654, Username="fixture", FullName="Fixture", Role=role)
            response = self.client.post("/login", json={"username": " fixture ", "password": "FixtureOnly123!"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json["role"], role)
            with self.client.session_transaction() as session:
                self.assertEqual(session["role"], role)
                if role == "Shipper":
                    token = session["shipper_session_token"]
                    self.assertEqual(self.cursor.execute.call_args.args[1], (token, 987654))
            if role == "Shipper":
                self.assertEqual(self.client.get("/logout").status_code, 302)
                self.assertEqual(self.cursor.execute.call_args.args[1], (987654, token))

    def test_staff_invalid_login(self):
        self.assertEqual(self.client.post("/login", json={}).status_code, 400)
        self.assertEqual(self.client.post("/login", json={"username": "fixture", "password": "FixtureOnly123!"}).status_code, 401)

    def test_checkout_both_payment_methods(self):
        for method in ("CASH", "BANK_TRANSFER"):
            self.customer()
            self.connection.reset_mock()
            self.cursor.fetchall.return_value = [Row(ProductID=987654, IsActive=True, IsAvailable=True)]
            response = self.client.post("/api/orders", json={**self.checkout, "paymentMethod": method})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json["totalAmount"], 220)
            self.assertEqual(response.json["paymentMethod"], method)
            self.assertEqual(self.cursor.execute.call_args_list[0].args[1], (987654,))
            self.connection.commit.assert_called_once()
            with self.client.session_transaction() as session:
                self.assertNotIn("checkout_verified_email", session)

    def test_checkout_otp_is_enforced(self):
        self.customer(verified=False)
        self.assertEqual(self.client.post("/api/orders", json=self.checkout).status_code, 403)
        self.customer()
        response = self.client.post("/api/orders", json={**self.checkout, "email": "other@example.com"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json["code"], "EMAIL_CHANGED_AFTER_VERIFY")
        self.connection.cursor.assert_not_called()

    def test_checkout_requires_login_and_unexpired_otp(self):
        self.customer()
        with self.client.session_transaction() as session:
            session.pop("customer_id")
        self.assertEqual(self.client.post("/api/orders", json=self.checkout).status_code, 401)
        self.customer()
        with self.client.session_transaction() as session:
            session["checkout_verified_email_at"] = int(time.time()) - 3600
        self.assertEqual(self.client.post("/api/orders", json=self.checkout).status_code, 403)
        self.connection.cursor.assert_not_called()

    def test_checkout_multiple_product_placeholders(self):
        self.customer()
        self.cursor.fetchall.return_value = [Row(ProductID=value, IsActive=True, IsAvailable=True) for value in (987654, 987655)]
        response = self.client.post("/api/orders", json={**self.checkout, "products": [*self.checkout["products"], {"id": 987655, "quantity": 1, "price": 50}]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["totalAmount"], 270)
        self.assertEqual(self.cursor.execute.call_args_list[0].args[1], (987654, 987655))

    def test_contact_write_failure_rollback(self):
        self.cursor.execute.side_effect = RuntimeError("fixture")
        with patch("builtins.print"):
            response = self.client.post("/api/contact", json={"fullName": "Fixture", "phone": "0900000000", "subject": "Khác", "message": "Fixture"})
        self.assertEqual(response.status_code, 500)
        self.connection.rollback.assert_called_once()
        self.connection.close.assert_called_once()

    def test_checkout_rejects_missing_or_unavailable_products(self):
        for rows in ([], [Row(ProductID=987654, IsActive=False, IsAvailable=True)], [Row(ProductID=987654, IsActive=True, IsAvailable=False)]):
            self.customer()
            self.connection.reset_mock()
            self.cursor.fetchall.return_value = rows
            self.assertEqual(self.client.post("/api/orders", json=self.checkout).status_code, 409)
            self.connection.rollback.assert_called_once()
            self.connection.commit.assert_not_called()
            with self.client.session_transaction() as session:
                self.assertIn("checkout_verified_email", session)

    def test_checkout_failure_rolls_back_and_retains_otp(self):
        self.customer()
        self.cursor.fetchall.return_value = [Row(ProductID=987654, IsActive=True, IsAvailable=True)]
        self.cursor.execute.side_effect = [None, RuntimeError("fixture")]
        with patch("builtins.print"):
            self.assertEqual(self.client.post("/api/orders", json=self.checkout).status_code, 500)
        self.connection.rollback.assert_called_once()
        with self.client.session_transaction() as session:
            self.assertIn("checkout_verified_email", session)

    def test_checkout_validation(self):
        for updates in ({"paymentMethod": "invalid"}, {"products": []}, {"products": [{"id": -1}]}, {"address": ""}):
            self.customer()
            self.assertEqual(self.client.post("/api/orders", json={**self.checkout, **updates}).status_code, 400)
        self.connection.cursor.assert_not_called()

    def test_payment_report_and_confirmed_payment(self):
        for payment, status, expected in (("CASH", "", 400), ("BANK_TRANSFER", "Chờ khách chuyển khoản", 200), ("BANK_TRANSFER", "Đã thanh toán", 200)):
            self.connection.reset_mock()
            self.cursor.fetchone.return_value = Row(OrderID=987654, PaymentMethod=payment, PaymentStatus=status)
            response = self.client.post("/api/orders/FIXTURE/payment-reported", json={"phone": "0900000000"})
            self.assertEqual(response.status_code, expected)
            self.assert_locked(0, "Orders")
            if status == "Đã thanh toán":
                self.assertEqual(response.json["paymentStatus"], status)
                self.assertEqual(self.cursor.execute.call_count, 1)

    def test_order_history(self):
        self.cursor.fetchall.return_value = [Row(OrderID=987654, OrderCode="FIXTURE", CustomerName="Fixture", Address="Fixture", TotalMoney=100, ShippingFee=None, Status="Đã tiếp nhận", CreatedTime=None, Latitude=10, Longitude=106, DriverID=None, DriverName=None)]
        response = self.client.get("/api/orders/0900000000")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json[0]["total"], 100)
        self.assertEqual(response.json[0]["createdAt"], "")

    def test_tracking_with_location(self):
        self.cursor.fetchone.side_effect = [Row(OrderCode="FIXTURE", Status="Đang giao", DriverID=987654, CustomerLatitude=10, CustomerLongitude=106, DriverName="Fixture"), Row(Latitude=11, Longitude=107, AgeSeconds=20, UpdatedTime="02/01/2026 03:04")]
        response = self.client.get("/api/orders/FIXTURE/tracking?phone=0900000000")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["destination"]["latitude"], 10)
        self.assertEqual(response.json["driver"]["latitude"], 11)
        self.assertTrue(response.json["driver"]["isFresh"])

    def test_tracking_validation_and_missing(self):
        self.assertEqual(self.client.get("/api/orders/FIXTURE/tracking").status_code, 400)
        self.assertEqual(self.client.get("/api/orders/FIXTURE/tracking?phone=0900000000").status_code, 404)

    def test_contact_create_and_order_verification(self):
        data = {"fullName": "Fixture", "phone": "0900000000", "email": "fixture@example.com", "subject": "Khác", "message": "Fixture"}
        for code in ("", "FIXTURE"):
            self.connection.reset_mock()
            self.cursor.fetchone.return_value = (987654,)
            response = self.client.post("/api/contact", json={**data, "orderCode": code})
            self.assertEqual(response.status_code, 200)
            self.connection.commit.assert_called_once()


class LocalOrderTests(OrderChecks, unittest.TestCase):
    mode = "local"


class PostgresOrderTests(OrderChecks, unittest.TestCase):
    mode = "postgres"


class QueryIntegrityTests(unittest.TestCase):
    def test_all_static_sql_keeps_vietnamese_literals(self):
        for module in (main, admin_orders, shipper):
            tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8-sig"))
            for call in ast.walk(tree):
                if not isinstance(call, ast.Call):
                    continue
                if isinstance(call.func, ast.Attribute) and call.func.attr == "execute":
                    self.fail(f"Unmigrated cursor.execute in {module.__name__}")
                if not isinstance(call.func, ast.Name) or call.func.id != "execute_query":
                    continue
                local, postgres = call.args[1:3]
                if not isinstance(local, ast.Constant) or not isinstance(postgres, ast.Constant):
                    continue
                def literals(sql):
                    return {value for value in re.findall(r"N?'([^']*)'", sql) if any(ord(char) > 127 for char in value)}
                self.assertEqual(literals(local.value), literals(postgres.value), f"Dialect literals differ in {module.__name__}:{call.lineno}")

    def test_duplicate_shipper_transition_serializes(self):
        """Model row locks/commits; this does not claim real-engine concurrency testing."""
        for mode in ("local", "postgres"):
            with self.subTest(mode=mode):
                user_lock = Lock()
                first_locked = Event()
                second_waiting = Event()
                state = {"status": "Đã giao shipper"}
                connections = []

                def connect():
                    connection = MagicMock()
                    cursor = connection.cursor.return_value
                    cursor.rowcount = 1
                    index = len(connections)
                    connections.append(connection)
                    transaction = {"locked": False, "pending": None, "row": None}

                    def execute(sql, params):
                        if sql.lstrip().startswith("SELECT") and ("FROM Users" in sql or 'FROM "Users"' in sql):
                            if "FOR UPDATE" not in sql and "UPDLOCK" not in sql:
                                raise AssertionError("Session lookup must hold a row lock")
                            if index == 1:
                                second_waiting.set()
                            if not user_lock.acquire(timeout=5):
                                raise RuntimeError("Mock row lock timed out")
                            transaction["locked"] = True
                            transaction["row"] = (True, True, "fixture-token")
                            first_locked.set()
                        elif sql.lstrip().startswith("SELECT"):
                            if not transaction["locked"]:
                                raise AssertionError("Order lookup preceded session lock")
                            transaction["row"] = (state["status"],)
                        else:
                            transaction["pending"] = params[0]

                    def release():
                        if transaction["locked"]:
                            transaction["locked"] = False
                            user_lock.release()

                    def commit():
                        if not second_waiting.wait(timeout=5):
                            raise RuntimeError("Concurrent request did not reach lock")
                        state["status"] = transaction["pending"]
                        release()

                    cursor.execute.side_effect = execute
                    cursor.fetchone.side_effect = lambda: transaction["row"]
                    connection.commit.side_effect = commit
                    connection.rollback.side_effect = release
                    connection.close.side_effect = release
                    return connection

                def transition():
                    with main.app.test_client() as client:
                        with client.session_transaction() as session:
                            session.update(role="Shipper", user_id=987654, shipper_session_token="fixture-token")
                        return client.post("/shipper/update/987654", json={"status": "Đang chuẩn bị"}).status_code

                with patch.dict(os.environ, {"DB_MODE": mode}), patch.dict(main.app.config, TESTING=True, SECRET_KEY="isolated-concurrency-test-key"), patch.object(shipper, "get_connection", side_effect=connect):
                    with ThreadPoolExecutor(max_workers=2) as executor:
                        first = executor.submit(transition)
                        self.assertTrue(first_locked.wait(timeout=5))
                        second = executor.submit(transition)
                        self.assertEqual(first.result(timeout=10), 200)
                        self.assertEqual(second.result(timeout=10), 400)
                self.assertEqual(state["status"], "Đang chuẩn bị")
                connections[0].commit.assert_called_once()
                connections[1].commit.assert_not_called()
                connections[1].rollback.assert_called_once()


def run_live_selects():
    # Build the SQL catalog through the real routes with mocked connections first.
    outcome = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if not outcome.wasSuccessful():
        return 1
    failures = 0
    snapshots = {}
    column_names = {}
    for mode in ("local", "postgres"):
        connection = None
        try:
            with patch.dict(os.environ, {"DB_MODE": mode}), patch.object(database, "_ensure_product_availability_column", lambda conn: None):
                connection = database.get_connection()
                cursor = connection.cursor()
                count = 0
                snapshots[mode] = []
                column_names[mode] = []
                try:
                    for (query, params) in SELECT_CATALOG[mode]:
                        if "FOR UPDATE" in query or "UPDLOCK" in query:
                            continue  # Do not lock production rows.
                        if params:
                            cursor.execute(query, params)
                        else:
                            cursor.execute(query)
                        names = [column[0] for column in cursor.description]
                        column_names[mode].append(names)
                        if mode == "postgres" and len(names) != len(set(names)):
                            raise AssertionError("Duplicate result columns")
                        snapshots[mode].append([tuple(row) for row in cursor.fetchall()])
                        count += 1
                    print(f"{mode}: {count} unlocked SELECT variants PASS (no data printed)")
                finally:
                    cursor.close()
        except Exception as error:
            failures += 1
            print(f"{mode}: SELECT checks FAIL ({type(error).__name__})")
        finally:
            if connection is not None:
                connection.close()
    if len(snapshots) == 2 and not failures:
        differences = [index + 1 for index, (local, postgres) in enumerate(zip(snapshots["local"], snapshots["postgres"])) if local != postgres]
        if len(snapshots["local"]) != len(snapshots["postgres"]):
            differences.append("variant count")
        print("Cross-backend SELECT result differences:", differences or "NONE")
        for variant in differences:
            if not isinstance(variant, int):
                continue
            left = snapshots["local"][variant - 1]
            right = snapshots["postgres"][variant - 1]
            if len(left) != len(right):
                print(f"Variant {variant}: row counts differ ({len(left)} vs {len(right)})")
                continue
            fields = {}
            date_deltas = {}
            null_differences = {}
            for local_row, postgres_row in zip(left, right):
                for name, local_value, postgres_value in zip(column_names["local"][variant - 1], local_row, postgres_row):
                    if local_value != postgres_value:
                        fields[name] = fields.get(name, 0) + 1
                        if (local_value is None) != (postgres_value is None):
                            null_differences[name] = null_differences.get(name, 0) + 1
                        if isinstance(local_value, datetime) and isinstance(postgres_value, datetime):
                            delta = abs((local_value.replace(tzinfo=None) - postgres_value.replace(tzinfo=None)).total_seconds())
                            date_deltas[name] = max(date_deltas.get(name, 0), delta)
            print(f"Variant {variant}: differing columns/counts (no values):", fields)
            print(f"Variant {variant}: max timestamp differences in seconds:", date_deltas, "; NULL mismatches:", null_differences)
    return failures


if __name__ == "__main__":
    for source in (Path(__file__), Path(main.__file__), Path(admin_orders.__file__), Path(shipper.__file__)):
        ast.parse(source.read_text(encoding="utf-8-sig"))
    if sys.argv[1:] == ["--live"]:
        raise SystemExit(bool(run_live_selects()))
    unittest.main()
