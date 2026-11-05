"""Shipper administration tests: mocked writes and optional SELECT-only checks."""

import ast
from collections import namedtuple
from datetime import datetime
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

from flask import Flask

import database
from routes import admin_shippers as shippers


Shipper = namedtuple("Shipper", "UserID FullName IsActive")


def make_app():
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="isolated-shipper-test-key")
    app.register_blueprint(shippers.admin_shippers_bp)
    app.add_url_rule("/login", "login", lambda: "login")
    return app


class ShipperChecks:
    def setUp(self):
        self.client = make_app().test_client()
        self.connection = MagicMock()
        self.cursor = self.connection.cursor.return_value
        self.cursor.fetchone.return_value = None
        self.data = {"username": " fixture_shipper ", "password": "FixtureOnly123!", "fullname": " Fixture Name ", "phone": " 0900000000 "}
        for replacement in (
            patch.dict(os.environ, {"DB_MODE": self.mode}),
            patch.object(shippers, "get_connection", return_value=self.connection),
        ):
            replacement.start()
            self.addCleanup(replacement.stop)
        render = patch.object(shippers, "render_template", return_value="shippers")
        self.render = render.start()
        self.addCleanup(render.stop)
        with self.client.session_transaction() as session:
            session["role"] = "Admin"
            session["marker"] = "unchanged"

    def assert_sql(self, index, params=()):
        args = self.cursor.execute.call_args_list[index].args
        self.assertEqual(args[1:], (params,) if params else ())
        query = args[0]
        self.assertEqual(query.count("%s" if self.mode == "postgres" else "?"), len(params))
        if self.mode == "postgres":
            for incompatible in ("?", "ISNULL", "GETDATE", "N'"):
                self.assertNotIn(incompatible, query)
            self.assertIn('"Users"' if index == 0 else '"', query)
        return query

    def test_list_statistics_and_session(self):
        row_type = namedtuple("Activity", "UserID Username FullName Phone IsActive IsWorking ActiveOrders TodayCompleted FailedOrders LastLocationAt")
        row = row_type(17, "fixture_shipper", "Fixture", "", True, False, 3, 2, 1, datetime(2026, 1, 2))
        self.cursor.fetchall.return_value = [row]
        self.assertEqual(self.client.get("/admin/shippers").status_code, 200)
        self.assertEqual(self.render.call_args.args, ("admin/shippers.html",))
        self.assertEqual(self.render.call_args.kwargs["shippers"], [row])
        sql = self.assert_sql(0)
        if self.mode == "postgres":
            for alias in ("ActiveOrders", "TodayCompleted", "FailedOrders", "LastLocationAt"):
                self.assertIn(f'AS "{alias}"', sql)
            self.assertIn('COALESCE(co."DeliveredAt", co."CreatedAt")', sql)
            self.assertIn("CURRENT_DATE", sql)
        self.connection.commit.assert_not_called()
        with self.client.session_transaction() as session:
            self.assertEqual(session["marker"], "unchanged")
            self.assertEqual(session["role"], "Admin")

    def test_add(self):
        response = self.client.post("/admin/shippers/add", json=self.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"success": True, "message": "Thêm shipper thành công."})
        self.assert_sql(0, ("fixture_shipper",))
        query = self.assert_sql(1, ("fixture_shipper", "FixtureOnly123!", "Fixture Name", "0900000000"))
        if self.mode == "postgres":
            self.assertIn("TRUE, FALSE", query)
        self.connection.commit.assert_called_once()
        self.connection.close.assert_called_once()

    def test_duplicate_username(self):
        for operation in ("add", "update/17"):
            self.connection.reset_mock()
            self.cursor.fetchone.return_value = (18,)
            response = self.client.post(f"/admin/shippers/{operation}", json=self.data)
            self.assertEqual(response.status_code, 400)
            self.assertFalse(response.json["success"])
            self.assertEqual(self.cursor.execute.call_count, 1)
            self.connection.commit.assert_not_called()
            self.connection.close.assert_called_once()

    def test_update_with_and_without_password(self):
        for password in ("", "FixtureNew123!"):
            self.connection.reset_mock()
            self.cursor.fetchone.side_effect = [None, (17,)]
            response = self.client.post("/admin/shippers/update/17", json={**self.data, "password": password})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json, {"success": True, "message": "Cập nhật shipper thành công."})
            self.assert_sql(0, ("fixture_shipper", 17))
            self.assert_sql(1, (17,))
            params = ("fixture_shipper",) + ((password,) if password else ()) + ("Fixture Name", "0900000000", 17)
            query = self.assert_sql(2, params)
            if not password:
                self.assertNotIn("Password", query)
            # Preserve existing session-token behavior; do not silently revoke sessions.
            self.assertNotIn("ActiveSessionToken", query)
            self.connection.commit.assert_called_once()

    def test_missing_shipper(self):
        self.cursor.fetchone.side_effect = [None, None]
        self.assertEqual(self.client.post("/admin/shippers/update/17", json=self.data).status_code, 404)
        self.connection.commit.assert_not_called()

    def test_lock_unlock_and_shift_reset(self):
        for value in (0, 1, False, True):
            self.connection.reset_mock()
            self.cursor.fetchone.side_effect = [Shipper(17, "Fixture", True), (0,)]
            response = self.client.post("/admin/shippers/status/17", json={"isActive": value})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json, {"success": True, "message": "Cập nhật trạng thái shipper thành công."})
            self.assert_sql(0, (17,))
            if not value:
                self.assert_sql(1, (17,))
            query = self.assert_sql(1 if value else 2, (17,))
            if self.mode == "postgres":
                self.assertIn('"IsWorking" = FALSE', query)
                self.assertIn('"IsActive" = ' + ("TRUE" if value else "FALSE"), query)
            else:
                self.assertIn("IsWorking = 0", query)
            self.connection.commit.assert_called_once()

    def test_cannot_lock_with_active_orders(self):
        self.cursor.fetchone.side_effect = [Shipper(17, "Fixture", True), (3,)]
        response = self.client.post("/admin/shippers/status/17", json={"isActive": False})
        self.assertEqual(response.status_code, 400)
        self.assertIn("3 đơn", response.json["message"])
        self.assertEqual(self.cursor.execute.call_count, 2)
        self.connection.commit.assert_not_called()

    def test_status_missing_shipper(self):
        self.assertEqual(self.client.post("/admin/shippers/status/17", json={"isActive": False}).status_code, 404)
        self.connection.commit.assert_not_called()

    def test_validation(self):
        for endpoint, data in (("add", {}), ("update/17", {}), ("status/17", {"isActive": "true"}), ("status/17", {"isActive": 2}), ("status/17", {})):
            self.assertEqual(self.client.post(f"/admin/shippers/{endpoint}", json=data).status_code, 400)
        self.connection.cursor.assert_not_called()

    def test_errors_do_not_commit_and_close_transaction(self):
        # Existing routes use DB-API close (implicit rollback), not explicit rollback.
        for endpoint, data, reads in (("add", self.data, [None]), ("update/17", self.data, [None, (17,)]), ("status/17", {"isActive": False}, [Shipper(17, "Fixture", True), (0,)])):
            for stage in ("select", "write", "commit"):
                with self.subTest(endpoint=endpoint, stage=stage):
                    self.connection.reset_mock()
                    self.cursor.fetchone.side_effect = list(reads)
                    self.cursor.execute.side_effect = ([RuntimeError("fixture")] if stage == "select" else [None] * len(reads) + [RuntimeError("fixture")] if stage == "write" else None)
                    self.connection.commit.side_effect = RuntimeError("fixture") if stage == "commit" else None
                    with self.assertRaises(RuntimeError):
                        self.client.post(f"/admin/shippers/{endpoint}", json=data)
                    if stage != "commit":
                        self.connection.commit.assert_not_called()
                    self.cursor.close.assert_called_once()
                    self.connection.close.assert_called_once()
                    self.connection.rollback.assert_not_called()

    def test_authorization(self):
        with self.client.session_transaction() as session:
            session["role"] = "Shipper"
        self.assertEqual(self.client.get("/admin/shippers").status_code, 302)
        for endpoint in ("add", "update/17", "status/17"):
            self.assertEqual(self.client.post(f"/admin/shippers/{endpoint}", json=self.data).status_code, 403)
        self.connection.cursor.assert_not_called()


class LocalShipperTests(ShipperChecks, unittest.TestCase):
    mode = "local"


class PostgresShipperTests(ShipperChecks, unittest.TestCase):
    mode = "postgres"


def run_live_checks():
    failures = 0
    for mode in ("local", "postgres"):
        try:
            with patch.dict(os.environ, {"DB_MODE": mode}):
                def connect_without_ddl():
                    with patch.object(database, "_ensure_product_availability_column", lambda conn: None):
                        return database.get_connection()

                def select_only(cursor, local_sql, postgres_sql, *params):
                    sql = postgres_sql if mode == "postgres" else local_sql
                    if not sql.lstrip().upper().startswith("SELECT"):
                        raise AssertionError("SELECT only")
                    return database.execute_query(cursor, local_sql, postgres_sql, *params)

                client = make_app().test_client()
                with client.session_transaction() as session:
                    session["role"] = "Admin"
                with patch.object(shippers, "get_connection", side_effect=connect_without_ddl), patch.object(shippers, "execute_query", side_effect=select_only), patch.object(shippers, "render_template", return_value="shippers") as render:
                    if client.get("/admin/shippers").status_code != 200:
                        raise AssertionError("Listing failed")
                    rows = render.call_args.kwargs["shippers"]
                    for row in rows:
                        if row.UserID != row[0]:
                            raise AssertionError("Row access mismatch")
                        for field in ("ActiveOrders", "TodayCompleted", "FailedOrders"):
                            if not isinstance(getattr(row, field), int) or getattr(row, field) < 0:
                                raise AssertionError("Invalid statistic")
                        if row.LastLocationAt is not None and not isinstance(row.LastLocationAt, datetime):
                            raise AssertionError("Invalid location timestamp")
                    print(f"{mode}: SELECT list/statistics/row access PASS ({len(rows)} shippers)")
                if mode == "postgres":
                    connection = connect_without_ddl()
                    try:
                        cursor = connection.cursor()
                        try:
                            cursor.execute("""SELECT indexdef FROM pg_indexes
                                WHERE schemaname = current_schema() AND tablename = 'Users'
                                  AND indexdef LIKE 'CREATE UNIQUE INDEX%'""")
                            definitions = [row[0] for row in cursor.fetchall()]
                            print("postgres: Users unique index metadata:", definitions)
                        finally:
                            cursor.close()
                    finally:
                        connection.close()
        except Exception as error:
            failures += 1
            print(f"{mode}: SELECT checks FAIL ({type(error).__name__})")
    return failures


if __name__ == "__main__":
    for source in (Path(__file__), Path(shippers.__file__)):
        ast.parse(source.read_text(encoding="utf-8-sig"))
    if sys.argv[1:] == ["--live"]:
        raise SystemExit(bool(run_live_checks()))
    unittest.main()
