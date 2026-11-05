"""Admin contacts regression tests; --live runs SELECT-only route checks."""

import ast
from datetime import datetime
from decimal import Decimal
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

from flask import Flask

import database
from routes import admin_contacts as contacts


def make_app():
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="isolated-admin-contact-test-key")
    app.register_blueprint(contacts.admin_contacts_bp)
    app.add_url_rule("/login", "login", lambda: "login")
    return app


class ContactChecks:
    def setUp(self):
        self.app = make_app()
        self.client = self.app.test_client()
        self.connection = MagicMock()
        self.cursor = self.connection.cursor.return_value
        self.cursor.fetchone.side_effect = [(4, 2, 1, 1), (3,), (2,)]
        self.cursor.fetchall.return_value = []
        for replacement in (
            patch.dict(os.environ, {"DB_MODE": self.mode}),
            patch.object(contacts, "get_connection", return_value=self.connection),
        ):
            replacement.start()
            self.addCleanup(replacement.stop)
        render = patch.object(contacts, "render_template", return_value="contacts page")
        self.render = render.start()
        self.addCleanup(render.stop)
        with self.client.session_transaction() as session:
            session["role"] = "Admin"
            session["fullname"] = "Fixture Admin"

    def assert_query(self, index, params=()):
        args = self.cursor.execute.call_args_list[index].args
        sql = args[0]
        self.assertEqual(args[1:], (params,) if params else ())
        token = "%s" if self.mode == "postgres" else "?"
        self.assertEqual(sql.count(token), len(params))
        if self.mode == "postgres":
            self.assertNotIn("?", sql)
            self.assertNotIn("ISNULL", sql)
            self.assertNotIn("SYSDATETIME", sql)
            self.assertNotIn("N'", sql)
        return sql

    def test_authorization(self):
        with self.client.session_transaction() as session:
            session["role"] = "Shipper"
        response = self.client.get("/admin/contacts")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/login"))
        for method, url in (("GET", "/admin/contacts/17"), ("POST", "/admin/contacts/17/status")):
            self.assertEqual(self.client.open(url, method=method, json={}).status_code, 403)
        self.connection.cursor.assert_not_called()

    def test_list_and_statistics(self):
        self.assertEqual(self.client.get("/admin/contacts").status_code, 200)
        context = self.render.call_args.kwargs
        for key, expected in {"total_contacts": 4, "new_contacts": 2, "processing_contacts": 1, "replied_contacts": 1, "pending_orders": 3, "online_shippers": 2}.items():
            self.assertEqual(context[key], expected)
        self.assertEqual(context["username"], "Fixture Admin")
        self.assertEqual(self.cursor.execute.call_count, 4)
        for index in range(4):
            self.assert_query(index)
        if self.mode == "postgres":
            self.assertIn('"IsActive" = TRUE', self.cursor.execute.call_args_list[2].args[0])
            self.assertIn('AS "OrderStatus"', self.cursor.execute.call_args.args[0])
        self.connection.commit.assert_not_called()
        self.cursor.close.assert_called_once()
        self.connection.close.assert_called_once()

    def test_empty_statistics(self):
        self.cursor.fetchone.side_effect = [(0, None, None, None), (0,), (0,)]
        self.assertEqual(self.client.get("/admin/contacts").status_code, 200)
        context = self.render.call_args.kwargs
        for key in ("total_contacts", "new_contacts", "processing_contacts", "replied_contacts", "pending_orders", "online_shippers"):
            self.assertEqual(context[key], 0)

    def test_search_filter_combinations_are_parameterized(self):
        keyword = "x' OR 1=1 --%_"
        for status in ("", "Mới"):
            for subject in ("", "Thanh toán"):
                for search in ("", keyword):
                    with self.subTest(status=status, subject=subject, search=search):
                        self.cursor.reset_mock()
                        self.cursor.fetchone.side_effect = [(4, 2, 1, 1), (3,), (2,)]
                        response = self.client.get("/admin/contacts", query_string={"status": status, "subject": subject, "q": search})
                        self.assertEqual(response.status_code, 200)
                        params = tuple(value for value in (status, subject) if value)
                        if search:
                            params += (f"%{search}%",) * 5
                        sql = self.assert_query(3, params)
                        self.assertNotIn(keyword, sql)
                        if search:
                            self.assertIn("COALESCE" if self.mode == "postgres" else "ISNULL", sql)

    def test_invalid_filters_ignored(self):
        response = self.client.get("/admin/contacts", query_string={"status": "invalid'", "subject": "invalid'"})
        self.assertEqual(response.status_code, 200)
        self.assert_query(3)
        self.assertEqual(self.render.call_args.kwargs["selected_status"], "")
        self.assertEqual(self.render.call_args.kwargs["selected_subject"], "")

    def test_detail_json_and_alias(self):
        self.cursor.fetchone.side_effect = None
        self.cursor.fetchone.return_value = (17, "Fixture", "0900000000", None, "Khác", "TEST-ORDER", "Message", "Mới", None, datetime(2026, 1, 2, 3, 4), None, None, 42, "Đã tiếp nhận", Decimal("123.50"))
        response = self.client.get("/admin/contacts/17")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"success": True, "contact": {"id": 17, "fullName": "Fixture", "phone": "0900000000", "email": "", "subject": "Khác", "orderCode": "TEST-ORDER", "message": "Message", "status": "Mới", "adminNote": "", "createdAt": "02/01/2026 03:04", "updatedAt": "", "resolvedAt": "", "orderId": 42, "orderStatus": "Đã tiếp nhận", "finalMoney": 123.5}})
        sql = self.assert_query(0, (17,))
        self.assertIn('AS "OrderStatus"' if self.mode == "postgres" else "AS OrderStatus", sql)

    def test_missing_detail(self):
        self.cursor.fetchone.side_effect = None
        self.cursor.fetchone.return_value = None
        self.assertEqual(self.client.get("/admin/contacts/17").status_code, 404)
        self.connection.close.assert_called_once()

    def test_update_all_statuses(self):
        for status in sorted(contacts.ALLOWED_STATUSES):
            with self.subTest(status=status):
                self.connection.reset_mock()
                self.cursor.fetchone.side_effect = None
                self.cursor.fetchone.return_value = (17,)
                response = self.client.post("/admin/contacts/17/status", json={"status": status, "adminNote": " fixture note "})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json, {"success": True, "status": status, "message": "Cập nhật liên hệ thành công."})
                self.assert_query(0, (17,))
                sql = self.assert_query(1, (status, "fixture note", status, 17))
                self.assertIn("ELSE", sql)
                self.assertIn("NULL", sql)
                if self.mode == "postgres":
                    self.assertIn('"ResolvedAt" = CASE', sql)
                    self.assertIn("CURRENT_TIMESTAMP", sql)
                self.connection.commit.assert_called_once()
                self.connection.rollback.assert_not_called()

    def test_empty_note_and_missing_update(self):
        self.cursor.fetchone.side_effect = None
        self.cursor.fetchone.return_value = (17,)
        self.assertEqual(self.client.post("/admin/contacts/17/status", json={"status": "Mới"}).status_code, 200)
        self.assert_query(1, ("Mới", None, "Mới", 17))
        self.connection.reset_mock()
        self.cursor.fetchone.return_value = None
        self.assertEqual(self.client.post("/admin/contacts/17/status", json={"status": "Mới"}).status_code, 404)
        self.connection.commit.assert_not_called()
        self.assertEqual(self.cursor.execute.call_count, 1)

    def test_update_validation(self):
        for data in ({"status": "invalid"}, {"status": "Mới", "adminNote": "a" * 1001}):
            self.assertEqual(self.client.post("/admin/contacts/17/status", json=data).status_code, 400)
        self.connection.cursor.assert_not_called()

    def test_failures_rollback_and_close(self):
        for stage in ("select", "update", "commit"):
            with self.subTest(stage=stage):
                self.connection.reset_mock()
                self.cursor.fetchone.side_effect = None
                self.cursor.fetchone.return_value = (17,)
                self.cursor.execute.side_effect = {"select": [RuntimeError("fixture")], "update": [None, RuntimeError("fixture")], "commit": None}[stage]
                self.connection.commit.side_effect = RuntimeError("fixture") if stage == "commit" else None
                with patch("builtins.print"):
                    response = self.client.post("/admin/contacts/17/status", json={"status": "Đã phản hồi"})
                self.assertEqual(response.status_code, 500)
                self.assertFalse(response.json["success"])
                self.connection.rollback.assert_called_once()
                self.cursor.close.assert_called_once()
                self.connection.close.assert_called_once()


class LocalContactTests(ContactChecks, unittest.TestCase):
    mode = "local"


class PostgresContactTests(ContactChecks, unittest.TestCase):
    mode = "postgres"


def run_live_checks():
    failures = 0
    for mode in ("local", "postgres"):
        try:
            with patch.dict(os.environ, {"DB_MODE": mode}):
                def connect_without_ddl():
                    with patch.object(database, "_ensure_product_availability_column", lambda conn: None):
                        return database.get_connection()

                def select_only(cursor, sql_server, postgres, *params):
                    query = postgres if mode == "postgres" else sql_server
                    if not query.lstrip().upper().startswith("SELECT"):
                        raise AssertionError("Live checks permit SELECT only")
                    database.execute_query(cursor, sql_server, postgres, *params)
                    names = [column[0] for column in cursor.description]
                    if len(names) != len(set(names)):
                        raise AssertionError("Duplicate result column names")
                    return cursor

                client = make_app().test_client()
                with client.session_transaction() as session:
                    session["role"] = "Admin"
                with patch.object(contacts, "get_connection", side_effect=connect_without_ddl):
                    with patch.object(contacts, "execute_query", side_effect=select_only):
                        with patch.object(contacts, "render_template", return_value="contacts") as render:
                            for filters in ({}, {"status": "Mới", "subject": "Khác", "q": "phase2c-isolated-search"}, {"status": "invalid", "subject": "invalid"}):
                                if client.get("/admin/contacts", query_string=filters).status_code != 200:
                                    raise AssertionError("Contact listing failed")
                                if not filters:
                                    rows = render.call_args.kwargs["contacts"]
                                    contact_id = rows[0].ContactID if rows else 0
                            print(f"{mode}: real SELECT list/statistics/search/filters PASS")
                        response = client.get(f"/admin/contacts/{contact_id}")
                        if response.status_code != (200 if contact_id else 404):
                            raise AssertionError("Contact detail failed")
                        print(f"{mode}: real SELECT detail/unique aliases PASS (HTTP {response.status_code})")
        except Exception as error:
            failures += 1
            print(f"{mode}: live SELECT FAIL ({type(error).__name__}); remaining checks NOT RUN")
    return failures


if __name__ == "__main__":
    for source in (Path(__file__), Path(contacts.__file__)):
        ast.parse(source.read_text(encoding="utf-8-sig"))
    if sys.argv[1:] == ["--live"]:
        raise SystemExit(bool(run_live_checks()))
    unittest.main()
