"""Product route tests: mocked writes; --live permits SELECT-only checks."""

import ast
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from io import BytesIO
import os
from pathlib import Path
import sys
from threading import Event, Lock
import unittest
from unittest.mock import MagicMock, patch

from flask import Flask

import database
from routes import admin_products as products


def make_app():
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="isolated-product-test-key")
    app.register_blueprint(products.admin_products_bp)
    app.add_url_rule("/login", "login", lambda: "login")
    return app


class ProductChecks:
    def setUp(self):
        self.client = make_app().test_client()
        self.connection = MagicMock()
        self.cursor = self.connection.cursor.return_value
        self.cursor.rowcount = 1
        self.cursor.fetchone.side_effect = [(1,), None]
        self.cursor.fetchall.side_effect = [[], []]
        self.data = {"name": " Fixture Product ", "description": " Description ", "price": "123.50", "category": "1"}
        for replacement in (
            patch.dict(os.environ, {"DB_MODE": self.mode}),
            patch.object(products, "get_connection", return_value=self.connection),
        ):
            replacement.start()
            self.addCleanup(replacement.stop)
        render = patch.object(products, "render_template", return_value="products")
        self.render = render.start()
        self.addCleanup(render.stop)
        with self.client.session_transaction() as session:
            session["role"] = "Admin"

    def assert_sql(self, index, params=()):
        args = self.cursor.execute.call_args_list[index].args
        sql = args[0]
        self.assertEqual(args[1:], (params,) if params else ())
        placeholder = "%s" if self.mode == "postgres" else "?"
        self.assertEqual(sql.count(placeholder), len(params))
        if self.mode == "postgres":
            self.assertNotIn("?", sql)
            self.assertNotIn("UPDLOCK", sql)
            self.assertNotIn("HOLDLOCK", sql)
        return sql

    def test_lists_and_categories(self):
        for view, expected in (("active", True), ("archived", False), ("invalid", True)):
            self.cursor.reset_mock()
            self.cursor.fetchall.side_effect = [[], []]
            self.assertEqual(self.client.get("/admin/products", query_string={"view": view}).status_code, 200)
            self.assert_sql(0, (expected,))
            self.assert_sql(1)
            self.assertEqual(self.render.call_args.kwargs["product_view"], "archived" if view == "archived" else "active")
        self.connection.commit.assert_not_called()

    def test_add_and_lock_order(self):
        response = self.client.post("/admin/products/add", data=self.data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, {"success": True, "message": "Thêm sản phẩm thành công."})
        category_sql = self.assert_sql(0, (1,))
        duplicate_sql = self.assert_sql(1, (1, "Fixture Product"))
        insert_sql = self.assert_sql(2, ("Fixture Product", "Description", Decimal("123.50"), "", 1))
        if self.mode == "postgres":
            self.assertIn('FROM "Categories"', category_sql)
            self.assertIn("FOR UPDATE", category_sql)
            self.assertNotIn("FOR UPDATE", duplicate_sql)
            self.assertIn('BTRIM("ProductName")', duplicate_sql)
            self.assertIn("TRUE", insert_sql)
        else:
            self.assertIn("WITH (UPDLOCK, HOLDLOCK)", duplicate_sql)
        self.connection.commit.assert_called_once()
        self.connection.rollback.assert_not_called()
        self.connection.close.assert_called_once()

    def test_duplicates_include_archived_products(self):
        for active in (True, False):
            self.connection.reset_mock()
            self.cursor.fetchone.side_effect = [(1,), (17, active)]
            response = self.client.post("/admin/products/add", data=self.data)
            self.assertEqual(response.status_code, 409)
            if not active:
                self.assertIn("khôi phục", response.json["message"])
            self.assertEqual(self.cursor.execute.call_count, 2)
            self.connection.rollback.assert_called_once()
            self.connection.commit.assert_not_called()

    def test_missing_category(self):
        self.cursor.fetchone.side_effect = [None]
        self.assertEqual(self.client.post("/admin/products/add", data=self.data).status_code, 400)
        self.connection.rollback.assert_called_once()
        self.assertEqual(self.cursor.execute.call_count, 1)

    def test_add_validation(self):
        for updates in ({"name": ""}, {"price": "NaN"}, {"price": "0"}, {"category": "-1"}, {"category": "invalid"}):
            self.assertEqual(self.client.post("/admin/products/add", data={**self.data, **updates}).status_code, 400)
        self.assertEqual(self.client.post("/admin/products/add", data={**self.data, "image": (BytesIO(b"fixture"), "invalid.txt")}).status_code, 400)
        self.connection.cursor.assert_not_called()

    def test_add_failures_rollback(self):
        for stage in ("category", "duplicate", "insert", "commit"):
            with self.subTest(stage=stage):
                self.connection.reset_mock()
                self.cursor.fetchone.side_effect = [(1,), None]
                self.cursor.execute.side_effect = {
                    "category": [RuntimeError("fixture")],
                    "duplicate": [None, RuntimeError("fixture")],
                    "insert": [None, None, RuntimeError("fixture")],
                    "commit": None,
                }[stage]
                self.connection.commit.side_effect = RuntimeError("fixture") if stage == "commit" else None
                with patch.object(self.client.application, "logger"):
                    response = self.client.post("/admin/products/add", data=self.data)
                self.assertEqual(response.status_code, 500)
                self.connection.rollback.assert_called_once()
                self.cursor.close.assert_called_once()
                self.connection.close.assert_called_once()

    def test_add_image_cleanup_on_insert_failure(self):
        self.cursor.execute.side_effect = [None, None, RuntimeError("fixture")]
        with patch("werkzeug.datastructures.FileStorage.save") as save, patch.object(products.os, "makedirs"), patch.object(products.os.path, "exists", return_value=True), patch.object(products.os, "remove") as remove, patch.object(self.client.application, "logger"):
            response = self.client.post("/admin/products/add", data={**self.data, "image": (BytesIO(b"fixture"), "fixture.png")})
        self.assertEqual(response.status_code, 500)
        save.assert_called_once()
        remove.assert_called_once_with(save.call_args.args[0])
        self.connection.rollback.assert_called_once()

    def test_edit_with_and_without_image(self):
        for has_image in (False, True):
            self.connection.reset_mock()
            data = dict(self.data)
            if has_image:
                data["image"] = (BytesIO(b"fixture"), "fixture.png")
            with patch("werkzeug.datastructures.FileStorage.save") as save, patch.object(products.os, "makedirs"):
                response = self.client.post("/admin/products/edit/17", data=data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json, {"success": True})
            params = ("Fixture Product", "Description", "123.50", "1")
            if has_image:
                params += ("fixture.png",)
                save.assert_called_once()
            else:
                save.assert_not_called()
            self.assert_sql(0, params + (17,))
            self.connection.commit.assert_called_once()

    def test_edit_validation(self):
        self.assertEqual(self.client.post("/admin/products/edit/17", data={}).status_code, 400)
        self.connection.cursor.assert_not_called()

    def test_availability_boolean_and_validation(self):
        for value in (True, False):
            self.connection.reset_mock()
            response = self.client.post("/admin/products/availability/17", json={"isAvailable": value})
            self.assertEqual(response.status_code, 200)
            self.assert_sql(0, (value, 17))
            self.connection.commit.assert_called_once()
        for value in (1, "true", None):
            self.connection.reset_mock()
            self.assertEqual(self.client.post("/admin/products/availability/17", json={"isAvailable": value}).status_code, 400)
            self.connection.cursor.assert_not_called()

    def test_archive_restore_and_legacy_delete(self):
        for operation, method in (("archive", "POST"), ("restore", "POST"), ("delete", "DELETE")):
            self.connection.reset_mock()
            response = self.client.open(f"/admin/products/{operation}/17", method=method)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json, {"success": True})
            sql = self.assert_sql(0, (17,))
            if self.mode == "postgres":
                self.assertIn("TRUE" if operation == "restore" else "FALSE", sql)
            self.connection.commit.assert_called_once()

    def test_missing_rows_rollback(self):
        self.cursor.rowcount = 0
        for operation in ("availability", "archive", "restore"):
            self.connection.reset_mock()
            response = self.client.post(f"/admin/products/{operation}/17", json={"isAvailable": True})
            self.assertEqual(response.status_code, 404)
            self.connection.rollback.assert_called_once()
            self.connection.commit.assert_not_called()

    def test_legacy_write_errors_close_without_committing(self):
        # Preserve existing routes' finally/close behavior (no new explicit rollback).
        self.cursor.execute.side_effect = RuntimeError("fixture")
        for operation, method, data in (("edit", "POST", self.data), ("archive", "POST", {}), ("restore", "POST", {}), ("delete", "DELETE", {})):
            self.connection.reset_mock()
            with self.assertRaises(RuntimeError):
                self.client.open(f"/admin/products/{operation}/17", method=method, data=data)
            self.connection.commit.assert_not_called()
            self.connection.close.assert_called_once()

    def test_permissions(self):
        with self.client.session_transaction() as session:
            session["role"] = "Shipper"
        self.assertEqual(self.client.get("/admin/products").status_code, 302)
        for operation, method in (("add", "POST"), ("edit/17", "POST"), ("availability/17", "POST"), ("archive/17", "POST"), ("restore/17", "POST"), ("delete/17", "DELETE")):
            self.assertEqual(self.client.open(f"/admin/products/{operation}", method=method).status_code, 403)
        self.connection.cursor.assert_not_called()


class LocalProductTests(ProductChecks, unittest.TestCase):
    mode = "local"


class PostgresProductTests(ProductChecks, unittest.TestCase):
    mode = "postgres"


class ConcurrentAddTests(unittest.TestCase):
    def test_postgres_adds_serialize_on_existing_category(self):
        """Simulate row-lock/READ COMMITTED semantics; no real database writes."""
        category_lock = Lock()
        first_locked = Event()
        second_waiting = Event()
        committed_names = set()
        connections = []

        def connect():
            connection = MagicMock()
            cursor = connection.cursor.return_value
            state = {"locked": False, "pending": None, "row": None}
            index = len(connections)
            connections.append(connection)

            def execute(sql, params):
                if 'FROM "Categories"' in sql:
                    if "FOR UPDATE" not in sql:
                        raise AssertionError("Missing category lock")
                    if index == 1:
                        second_waiting.set()
                    if not category_lock.acquire(timeout=5):
                        raise RuntimeError("Simulated category lock timed out")
                    state["locked"] = True
                    first_locked.set()
                    state["row"] = (1,)
                elif sql.lstrip().startswith("SELECT"):
                    if not state["locked"]:
                        raise AssertionError("Duplicate lookup preceded category lock")
                    state["row"] = (17, True) if params[1].lower() in committed_names else None
                elif sql.lstrip().startswith("INSERT"):
                    state["pending"] = params[0].lower()
                else:
                    raise AssertionError("Unexpected query")

            def release():
                if state["locked"]:
                    state["locked"] = False
                    category_lock.release()

            def commit():
                if not second_waiting.wait(timeout=5):
                    raise RuntimeError("Second request never reached the lock")
                committed_names.add(state["pending"])
                release()

            cursor.execute.side_effect = execute
            cursor.fetchone.side_effect = lambda: state["row"]
            connection.commit.side_effect = commit
            connection.rollback.side_effect = release
            connection.close.side_effect = release
            return connection

        def add():
            with make_app().test_client() as client:
                with client.session_transaction() as session:
                    session["role"] = "Admin"
                return client.post("/admin/products/add", data={"name": "Concurrent Fixture", "price": "100", "category": "1"}).status_code

        with patch.dict(os.environ, {"DB_MODE": "postgres"}), patch.object(products, "get_connection", side_effect=connect):
            with ThreadPoolExecutor(max_workers=2) as executor:
                first = executor.submit(add)
                self.assertTrue(first_locked.wait(timeout=5))
                second = executor.submit(add)
                self.assertEqual(first.result(timeout=10), 201)
                self.assertEqual(second.result(timeout=10), 409)
        self.assertEqual(committed_names, {"concurrent fixture"})
        connections[0].commit.assert_called_once()
        connections[1].commit.assert_not_called()
        connections[1].rollback.assert_called_once()


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
                    if not query.lstrip().upper().startswith("SELECT") or "FOR UPDATE" in query:
                        raise AssertionError("Only unlocked SELECT allowed")
                    return database.execute_query(cursor, sql_server, postgres, *params)

                client = make_app().test_client()
                with client.session_transaction() as session:
                    session["role"] = "Admin"
                with patch.object(products, "get_connection", side_effect=connect_without_ddl), patch.object(products, "execute_query", side_effect=select_only), patch.object(products, "render_template", return_value="products") as render:
                    for view in ("active", "archived"):
                        if client.get("/admin/products", query_string={"view": view}).status_code != 200:
                            raise AssertionError("List failed")
                        context = render.call_args.kwargs
                        for row in context["products"]:
                            if row.ProductID != row[0]:
                                raise AssertionError("Product row access mismatch")
                        for row in context["categories"]:
                            if row.CategoryID != row[0]:
                                raise AssertionError("Category row access mismatch")
                        print(f"{mode}: SELECT {view} products/categories PASS ({len(context['products'])} products, {len(context['categories'])} categories)")
                if mode == "postgres":
                    connection = connect_without_ddl()
                    try:
                        cursor = connection.cursor()
                        try:
                            cursor.execute("""
                                SELECT indexdef FROM pg_indexes
                                WHERE schemaname = current_schema() AND tablename = 'Products'
                                  AND indexdef LIKE 'CREATE UNIQUE INDEX%'
                            """)
                            # Schema metadata only; never print product/customer data.
                            for row in cursor.fetchall():
                                print("postgres: unique index metadata:", row[0])
                        finally:
                            cursor.close()
                    finally:
                        connection.close()
        except Exception as error:
            failures += 1
            print(f"{mode}: SELECT checks FAIL ({type(error).__name__})")
    return failures


if __name__ == "__main__":
    for source in (Path(__file__), Path(products.__file__)):
        ast.parse(source.read_text(encoding="utf-8-sig"))
    if sys.argv[1:] == ["--live"]:
        raise SystemExit(bool(run_live_checks()))
    unittest.main()
