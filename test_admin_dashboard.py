"""Dashboard regression tests and optional read-only cross-backend checks."""

import ast
from collections import namedtuple
from decimal import Decimal
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

from flask import Flask

import database
from routes import admin


METRICS = ("today_orders", "today_completed", "today_collected", "pending_orders",
           "active_orders", "failed_orders", "active_products", "total_shippers", "online_shippers")
RecentOrder = namedtuple("RecentOrder", "OrderID OrderCode CustomerName FinalMoney Status CreatedTime ShipperName")


def make_app():
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="isolated-dashboard-test-key")
    app.register_blueprint(admin.admin_bp)
    app.add_url_rule("/login", "login", lambda: "login")
    return app


class DashboardChecks:
    def setUp(self):
        self.client = make_app().test_client()
        self.connection = MagicMock()
        self.cursor = self.connection.cursor.return_value
        self.cursor.fetchone.side_effect = [(5, 2, Decimal("123.50")), (1, 2, 3), (11,), (3, 2)]
        self.cursor.fetchall.return_value = [RecentOrder(17, "FIXTURE", "Fixture", Decimal("123.50"), "Hoàn thành", "02/01/2026 03:04", "Chưa giao shipper")]
        for replacement in (patch.dict(os.environ, {"DB_MODE": self.mode}), patch.object(admin, "get_connection", return_value=self.connection)):
            replacement.start()
            self.addCleanup(replacement.stop)
        render = patch.object(admin, "render_template", return_value="dashboard")
        self.render = render.start()
        self.addCleanup(render.stop)
        with self.client.session_transaction() as session:
            session["role"] = "Admin"
            session["fullname"] = "Fixture Admin"

    def test_dashboard_metrics_aliases_and_queries(self):
        self.assertEqual(self.client.get("/admin/dashboard").status_code, 200)
        context = self.render.call_args.kwargs
        self.assertEqual(self.render.call_args.args, ("admin/dashboard.html",))
        self.assertEqual([context[key] for key in METRICS], [5, 2, Decimal("123.50"), 1, 2, 3, 11, 3, 2])
        self.assertEqual(context["username"], "Fixture Admin")
        self.assertEqual(context["recent_orders"][0].CreatedTime, "02/01/2026 03:04")
        self.assertEqual(self.cursor.execute.call_count, 5)
        for call in self.cursor.execute.call_args_list:
            self.assertEqual(len(call.args), 1)
        sql = "\n".join(call.args[0] for call in self.cursor.execute.call_args_list)
        if self.mode == "postgres":
            for token in ("ISNULL", "GETDATE", "TOP ", "CONVERT", "N'"):
                self.assertNotIn(token, sql)
            for alias in ("TodayOrders", "TodayCompleted", "TodayCollected", "PendingOrders", "ActiveOrders", "FailedOrders", "TotalShippers", "OnlineShippers", "FinalMoney", "CreatedTime", "ShipperName"):
                self.assertIn(f'AS "{alias}"', sql)
            self.assertIn("COALESCE", sql)
            self.assertIn("CURRENT_DATE", sql)
            self.assertIn("LIMIT 6", sql)
            self.assertIn("DESC NULLS LAST", sql)
            self.assertIn("DD/MM/YYYY HH24:MI", sql)
        self.connection.commit.assert_not_called()
        self.connection.rollback.assert_not_called()
        self.cursor.close.assert_called_once()
        self.connection.close.assert_called_once()

    def test_empty_and_null_aggregates(self):
        self.cursor.fetchone.side_effect = [(0, None, None), (None, None, None), (0,), (0, None)]
        self.cursor.fetchall.return_value = []
        self.assertEqual(self.client.get("/admin/dashboard").status_code, 200)
        context = self.render.call_args.kwargs
        self.assertEqual([context[key] for key in METRICS], [0] * len(METRICS))
        self.assertEqual(context["recent_orders"], [])

    def test_default_admin_name(self):
        with self.client.session_transaction() as session:
            session.pop("fullname")
        self.client.get("/admin/dashboard")
        self.assertEqual(self.render.call_args.kwargs["username"], "Admin")

    def test_permissions(self):
        for role in (None, "Shipper", "Customer"):
            with self.client.session_transaction() as session:
                session["role"] = role
            for url in ("/admin/dashboard", "/admin/users", "/admin/categories"):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.location.endswith("/login"))
        self.connection.cursor.assert_not_called()

    def test_query_failure_closes_connection(self):
        self.cursor.execute.side_effect = RuntimeError("fixture")
        with self.assertRaises(RuntimeError):
            self.client.get("/admin/dashboard")
        self.connection.commit.assert_not_called()
        self.connection.close.assert_called_once()


class LocalDashboardTests(DashboardChecks, unittest.TestCase):
    mode = "local"


class PostgresDashboardTests(DashboardChecks, unittest.TestCase):
    mode = "postgres"


def fixture_cte(mode, empty):
    """SELECT-only CTEs shadow tables; exercise real SQL without stored fixtures."""
    if mode == "postgres":
        return """
            WITH "Orders" AS (
                SELECT 1 AS "OrderID", 'FIXTURE' AS "OrderCode", 'Fixture' AS "CustomerName",
                    NULL::numeric AS "TotalMoney", NULL::double precision AS "ShippingFee",
                    'Hoàn thành' AS "Status", CURRENT_TIMESTAMP::timestamp AS "CreatedAt",
                    NULL::integer AS "DriverID" WHERE %s
            ), "Products" AS (SELECT TRUE AS "IsActive" WHERE %s),
            "Users" AS (SELECT 1 AS "UserID", NULL::text AS "FullName", 'Shipper' AS "Role",
                TRUE AS "IsActive", FALSE AS "IsWorking" WHERE %s)
        """ % (("FALSE",) * 3 if empty else ("TRUE",) * 3)
    condition = "1 = 0" if empty else "1 = 1"
    return """
        ;WITH Orders AS (
            SELECT 1 AS OrderID, 'FIXTURE' AS OrderCode, 'Fixture' AS CustomerName,
                CAST(NULL AS DECIMAL(18,2)) AS TotalMoney, CAST(NULL AS FLOAT) AS ShippingFee,
                N'Hoàn thành' AS Status, GETDATE() AS CreatedAt,
                CAST(NULL AS INT) AS DriverID WHERE %s
        ), Products AS (SELECT CAST(1 AS BIT) AS IsActive WHERE %s),
        Users AS (SELECT 1 AS UserID, CAST(NULL AS NVARCHAR(100)) AS FullName, 'Shipper' AS Role,
            CAST(1 AS BIT) AS IsActive, CAST(0 AS BIT) AS IsWorking WHERE %s)
    """ % ((condition,) * 3)


def run_live_checks():
    failures = 0
    results = {}
    diagnostics = {}
    for mode in ("local", "postgres"):
        try:
            with patch.dict(os.environ, {"DB_MODE": mode}):
                def connect_without_ddl():
                    with patch.object(database, "_ensure_product_availability_column", lambda conn: None):
                        return database.get_connection()

                client = make_app().test_client()
                with client.session_transaction() as session:
                    session["role"] = "Admin"
                for scenario in ("stored", "empty", "null_money"):
                    def execute_select(cursor, local_sql, postgres_sql, *params):
                        query = postgres_sql if mode == "postgres" else local_sql
                        if not query.lstrip().upper().startswith("SELECT"):
                            raise AssertionError("SELECT only")
                        if scenario != "stored":
                            query = fixture_cte(mode, scenario == "empty") + query
                        cursor.execute(query)
                        names = [column[0] for column in cursor.description]
                        if len(names) != len(set(names)):
                            raise AssertionError("Duplicate aliases")
                        return cursor

                    with patch.object(admin, "get_connection", side_effect=connect_without_ddl), patch.object(admin, "execute_query", side_effect=execute_select), patch.object(admin, "render_template", return_value="dashboard") as render:
                        if client.get("/admin/dashboard").status_code != 200:
                            raise AssertionError("Dashboard failed")
                        context = render.call_args.kwargs
                        if scenario == "empty":
                            if any(context[key] != 0 for key in METRICS) or context["recent_orders"]:
                                raise AssertionError("Empty aggregate mismatch")
                        elif scenario == "null_money":
                            if [context[key] for key in METRICS] != [1, 1, 0, 0, 0, 0, 1, 1, 0]:
                                raise AssertionError("NULL aggregate mismatch")
                            row = context["recent_orders"][0]
                            if row.FinalMoney != 0 or row.ShipperName != "Chưa giao shipper":
                                raise AssertionError("NULL projection mismatch")
                        else:
                            results[mode] = {key: Decimal(str(context[key])) for key in METRICS}
                            results[mode]["recent_orders"] = [tuple(row) for row in context["recent_orders"]]
                        print(f"{mode}: dashboard SELECT {scenario} PASS")

                connection = connect_without_ddl()
                try:
                    cursor = connection.cursor()
                    try:
                        database.execute_query(cursor,
                            "SELECT CAST(GETDATE() AS DATE), DATEPART(TZOFFSET, SYSDATETIMEOFFSET())",
                            "SELECT CURRENT_DATE, EXTRACT(TIMEZONE FROM CURRENT_TIMESTAMP) / 60")
                        today, offset_minutes = cursor.fetchone()
                        database.execute_query(cursor,
                            "SELECT CreatedAt, Status, TotalMoney, ShippingFee FROM Orders",
                            'SELECT "CreatedAt", "Status", "TotalMoney", "ShippingFee" FROM "Orders"')
                        rows = cursor.fetchall()
                        monthly = {}
                        for created, status, money, fee in rows:
                            if status == "Hoàn thành":
                                month = created.strftime("%Y-%m") if created else "NULL"
                                monthly[month] = monthly.get(month, Decimal(0)) + Decimal(str(money or 0)) + Decimal(str(fee or 0))
                        diagnostics[mode] = {"monthly_completed_revenue": monthly, "order_count": len(rows)}
                        print(f"{mode}: database date {today}; UTC offset minutes {offset_minutes}; monthly/total revenue snapshot read")
                    finally:
                        cursor.close()
                finally:
                    connection.close()
        except Exception as error:
            failures += 1
            print(f"{mode}: live checks FAIL ({type(error).__name__})")
    if len(results) == 2:
        differences = [key for key in results["local"] if results["local"][key] != results["postgres"][key]]
        print("Dashboard cross-backend differences:", differences or "NONE")
    if len(diagnostics) == 2:
        print("Monthly revenue/order count snapshots equivalent:", diagnostics["local"] == diagnostics["postgres"])
    return failures


if __name__ == "__main__":
    for source in (Path(__file__), Path(admin.__file__)):
        ast.parse(source.read_text(encoding="utf-8-sig"))
    if sys.argv[1:] == ["--live"]:
        raise SystemExit(bool(run_live_checks()))
    unittest.main()
