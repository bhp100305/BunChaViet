"""Customer route regression tests. Writes are mocked; --live only reads."""

import ast
from collections import namedtuple
from contextlib import suppress
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

from flask import Flask

import database
from routes import customer_auth as auth


Customer = namedtuple("Customer", "CustomerID FullName Email Phone PasswordHash")
PASSWORD = "FixturePassword123!"
NEW_PASSWORD = "ChangedFixture123!"


def make_app():
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="isolated-customer-test-key")
    app.register_blueprint(auth.customer_auth_bp)
    return app


class CustomerChecks:
    @classmethod
    def setUpClass(cls):
        cls.stored_hash = auth.hash_password(PASSWORD)

    def setUp(self):
        self.app = make_app()
        self.client = self.app.test_client()
        self.connection = MagicMock()
        self.cursor = self.connection.cursor.return_value
        self.cursor.rowcount = 1
        self.cursor.fetchone.return_value = None
        self.customer = Customer(987654, "Test Customer", "fixture@example.com", "0900000000", self.stored_hash)
        self.env = patch.dict(os.environ, {"DB_MODE": self.mode})
        self.env.start()
        self.addCleanup(self.env.stop)
        connection_patch = patch.object(auth, "get_connection", return_value=self.connection)
        self.get_connection = connection_patch.start()
        self.addCleanup(connection_patch.stop)

    def login_session(self):
        with self.client.session_transaction() as session:
            session["customer_id"] = self.customer.CustomerID
            session["customer_name"] = self.customer.FullName

    def verified_session(self, email="fixture@example.com", age=0):
        with self.client.session_transaction() as session:
            session["checkout_verified_email"] = email
            session["checkout_verified_email_at"] = int(time.time()) - age

    def assert_sql(self, call_index, columns, params):
        query, values = self.cursor.execute.call_args_list[call_index].args
        self.assertEqual(values, params)
        if self.mode == "postgres":
            self.assertIn('"Customers"', query)
            for name in columns:
                self.assertIn(f'"{name}"', query)
            self.assertNotIn("?", query)
            self.assertEqual(query.count("%s"), len(params))
            if "IsActive" in columns:
                self.assertIn("TRUE", query)
        else:
            self.assertIn("Customers", query)
            self.assertNotIn("%s", query)
            self.assertEqual(query.count("?"), len(params))

    def test_invalid_login(self):
        response = self.client.post("/api/customer/login", json={"email": "missing@example.com", "password": PASSWORD})
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json["success"])
        self.assert_sql(0, ["Email", "PasswordHash", "IsActive"], ("missing@example.com",))
        self.connection.commit.assert_not_called()

    def test_valid_login_and_logout(self):
        self.cursor.fetchone.return_value = self.customer
        with self.client.session_transaction() as session:
            session["old_session_value"] = True
        response = self.client.post("/api/customer/login", json={"email": " FIXTURE@example.com ", "password": PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"success": True, "customer": {"id": self.customer.CustomerID, "email": self.customer.Email, "name": self.customer.FullName}, "redirect": "/"})
        with self.client.session_transaction() as session:
            self.assertEqual(session["customer_id"], self.customer.CustomerID)
            self.assertNotIn("old_session_value", session)
        self.assertEqual(self.client.post("/api/customer/logout").status_code, 200)
        self.assertEqual(self.client.get("/api/customer/session").json, {"authenticated": False})

    def test_wrong_password(self):
        self.cursor.fetchone.return_value = self.customer
        response = self.client.post("/api/customer/login", json={"email": self.customer.Email, "password": "IncorrectFixture123!"})
        self.assertEqual(response.status_code, 401)
        with self.client.session_transaction() as session:
            self.assertNotIn("customer_id", session)

    def test_unauthenticated_profile_and_writes(self):
        for method, endpoint in (("GET", "/api/customer/profile"), ("PUT", "/api/customer/profile"), ("POST", "/api/customer/password")):
            with self.subTest(endpoint=endpoint, method=method):
                response = self.client.open(endpoint, method=method, json={})
                self.assertEqual(response.status_code, 401)
        self.get_connection.assert_not_called()

    def test_get_profile(self):
        self.login_session()
        self.cursor.fetchone.return_value = self.customer
        response = self.client.get("/api/customer/profile")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"success": True, "profile": {"fullName": self.customer.FullName, "email": self.customer.Email, "phone": self.customer.Phone}})
        self.assert_sql(0, ["FullName", "Email", "Phone", "CustomerID", "IsActive"], (self.customer.CustomerID,))
        self.connection.commit.assert_not_called()
        self.cursor.close.assert_called_once()
        self.connection.close.assert_called_once()

    def test_missing_profile_clears_session(self):
        self.login_session()
        self.assertEqual(self.client.get("/api/customer/profile").status_code, 401)
        with self.client.session_transaction() as session:
            self.assertNotIn("customer_id", session)

    def test_update_profile(self):
        self.login_session()
        response = self.client.put("/api/customer/profile", json={"fullName": " Updated Name ", "phone": " 0911111111 "})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["profile"], {"fullName": "Updated Name", "phone": "0911111111"})
        self.assert_sql(0, ["FullName", "Phone", "CustomerID", "IsActive"], ("Updated Name", "0911111111", self.customer.CustomerID))
        self.connection.commit.assert_called_once()
        self.connection.rollback.assert_not_called()
        with self.client.session_transaction() as session:
            self.assertEqual(session["customer_name"], "Updated Name")

    def test_update_profile_missing_row_rolls_back(self):
        self.login_session()
        self.cursor.rowcount = 0
        response = self.client.put("/api/customer/profile", json={"fullName": "Updated Name", "phone": "0911111111"})
        self.assertEqual(response.status_code, 404)
        self.connection.rollback.assert_called_once()
        self.connection.commit.assert_not_called()

    def test_change_password(self):
        self.login_session()
        self.cursor.fetchone.return_value = self.customer
        response = self.client.post("/api/customer/password", json={"currentPassword": PASSWORD, "newPassword": NEW_PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["success"])
        self.assert_sql(0, ["PasswordHash", "CustomerID", "IsActive"], (self.customer.CustomerID,))
        new_hash, customer_id = self.cursor.execute.call_args.args[1]
        self.assertEqual(customer_id, self.customer.CustomerID)
        self.assertTrue(auth.verify_password(NEW_PASSWORD, new_hash))
        self.assertFalse(auth.verify_password(PASSWORD, new_hash))
        self.assert_sql(1, ["PasswordHash", "CustomerID", "IsActive"], (new_hash, customer_id))
        self.connection.commit.assert_called_once()

    def test_wrong_current_password_does_not_write(self):
        self.login_session()
        self.cursor.fetchone.return_value = self.customer
        response = self.client.post("/api/customer/password", json={"currentPassword": "WrongFixture123!", "newPassword": NEW_PASSWORD})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.cursor.execute.call_count, 1)
        self.connection.commit.assert_not_called()

    def test_registration_with_verified_email(self):
        self.verified_session()
        response = self.client.post("/api/customer/register", json={"fullName": "Test Customer", "phone": "0900000000", "email": "FIXTURE@example.com", "password": PASSWORD})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, {"success": True, "message": "Tạo tài khoản thành công.", "redirect": "/customer/login"})
        self.assert_sql(0, ["CustomerID", "Email"], ("fixture@example.com",))
        values = self.cursor.execute.call_args.args[1]
        self.assertEqual(values[:3], ("Test Customer", "fixture@example.com", "0900000000"))
        self.assertTrue(auth.verify_password(PASSWORD, values[3]))
        self.assert_sql(1, ["FullName", "Email", "Phone", "PasswordHash", "IsActive", "CreatedAt"], values)
        self.connection.commit.assert_called_once()
        with self.client.session_transaction() as session:
            self.assertNotIn("checkout_verified_email", session)

    def test_duplicate_email(self):
        self.verified_session()
        self.cursor.fetchone.return_value = self.customer
        response = self.client.post("/api/customer/register", json={"fullName": "Test Customer", "phone": "0900000000", "email": "fixture@example.com", "password": PASSWORD})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.cursor.execute.call_count, 1)
        self.connection.commit.assert_not_called()

    def test_registration_enforces_otp(self):
        for email, age in (("", 0), ("different@example.com", 0), ("fixture@example.com", auth.OTP_VALID_SECONDS + 10)):
            self.verified_session(email, age)
            response = self.client.post("/api/customer/register", json={"fullName": "Test Customer", "phone": "0900000000", "email": "fixture@example.com", "password": PASSWORD})
            self.assertEqual(response.status_code, 403)
        self.get_connection.assert_not_called()

    def test_write_failures_rollback_and_close(self):
        self.login_session()
        self.verified_session()
        cases = (
            ("PUT", "/api/customer/profile", {"fullName": "Updated Name", "phone": "0911111111"}, [RuntimeError("fixture failure")]),
            ("POST", "/api/customer/password", {"currentPassword": PASSWORD, "newPassword": NEW_PASSWORD}, [None, RuntimeError("fixture failure")]),
            ("POST", "/api/customer/register", {"fullName": "Test Customer", "phone": "0900000000", "email": "fixture@example.com", "password": PASSWORD}, [None, RuntimeError("fixture failure")]),
        )
        for method, endpoint, data, effects in cases:
            with self.subTest(endpoint=endpoint):
                self.connection.reset_mock()
                self.cursor.execute.side_effect = effects
                self.cursor.fetchone.return_value = self.customer if endpoint.endswith("password") else None
                response = self.client.open(endpoint, method=method, json=data)
                self.assertEqual(response.status_code, 500)
                self.assertFalse(response.json["success"])
                self.connection.rollback.assert_called_once()
                self.connection.commit.assert_not_called()
                self.cursor.close.assert_called_once()
                self.connection.close.assert_called_once()
                with self.client.session_transaction() as session:
                    self.assertEqual(session["customer_name"], self.customer.FullName)


class LocalCustomerTests(CustomerChecks, unittest.TestCase):
    mode = "local"


class PostgresCustomerTests(CustomerChecks, unittest.TestCase):
    mode = "postgres"


def run_live_checks():
    """Only use nonexistent-account login; never call a write endpoint."""
    failures = 0
    for mode in ("local", "postgres"):
        try:
            with patch.dict(os.environ, {"DB_MODE": mode}):
                # Prevent get_connection from running local schema DDL.
                with patch.object(database, "_ensure_product_availability_column", lambda connection: None):
                    connection = database.get_connection()
                    try:
                        with patch.object(auth, "get_connection", return_value=connection):
                            with make_app().test_client() as client:
                                response = client.post("/api/customer/login", json={"email": "not-existing-test@example.com", "password": "WrongPassword123!"})
                                if response.status_code != 401 or response.json["success"] is not False:
                                    raise AssertionError("Expected invalid-login response")
                                print(f"{mode}: real database invalid login PASS (HTTP 401)")
                    finally:
                        # The route normally closes it; tolerate already closed drivers.
                        with suppress(Exception):
                            connection.close()
        except Exception as error:
            failures += 1
            print(f"{mode}: real database invalid login FAIL ({type(error).__name__})")
    return failures


if __name__ == "__main__":
    for source in (Path(__file__), Path(auth.__file__)):
        ast.parse(source.read_text(encoding="utf-8-sig"))
    if sys.argv[1:] == ["--live"]:
        raise SystemExit(bool(run_live_checks()))
    unittest.main()
