"""Run unit tests normally; add --live for read-only database checks.

Live checks replace the existing SQL Server schema initializer with a SELECT
that verifies IsAvailable, so testing never executes DDL or commits.
"""

import ast
import builtins
from contextlib import closing
import os
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import MagicMock, patch

import database


class DatabaseConnectionTests(unittest.TestCase):
    def test_syntax(self):
        for name in ("database.py", "test_database_connection.py"):
            ast.parse(Path(__file__).with_name(name).read_text(encoding="utf-8-sig"))

    def test_modes(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(database.get_db_mode(), "local")
        with patch.dict(os.environ, {"DB_MODE": " POSTGRES "}):
            self.assertEqual(database.get_db_mode(), "postgres")
        with patch.dict(os.environ, {"DB_MODE": "unsupported"}):
            with self.assertRaises(ValueError):
                database.get_db_mode()

    def test_helper_parameters_and_transactions(self):
        for mode, expected in (("local", "SELECT ?"), ("postgres", "SELECT %s")):
            for params in ((), (7,), (7, "value"), (None, True), ([1, 2],)):
                with self.subTest(mode=mode, params=params):
                    cursor = MagicMock()
                    with patch.dict(os.environ, {"DB_MODE": mode}):
                        result = database.execute_query(cursor, "SELECT ?", "SELECT %s", *params)
                    self.assertIs(result, cursor)
                    if params:
                        cursor.execute.assert_called_once_with(expected, params)
                    else:
                        cursor.execute.assert_called_once_with(expected)
                    cursor.connection.commit.assert_not_called()
                    cursor.connection.rollback.assert_not_called()

    def test_helper_propagates_errors_without_transaction_changes(self):
        cursor = MagicMock()
        cursor.execute.side_effect = RuntimeError("query failed")
        with patch.dict(os.environ, {"DB_MODE": "postgres"}):
            with self.assertRaises(RuntimeError):
                database.execute_query(cursor, "SELECT ?", "SELECT %s", 1)
        cursor.connection.commit.assert_not_called()
        cursor.connection.rollback.assert_not_called()

    def test_lazy_drivers_and_schema_initialization(self):
        original_import = builtins.__import__
        for mode in ("local", "postgres"):
            with self.subTest(mode=mode):
                driver = ModuleType("pyodbc" if mode == "local" else "psycopg")
                connection = MagicMock()
                driver.connect = MagicMock(return_value=connection)
                rows = ModuleType("psycopg.rows")
                rows.namedtuple_row = object()
                modules = {driver.__name__: driver}
                if mode == "postgres":
                    modules["psycopg.rows"] = rows

                def guarded_import(name, *args, **kwargs):
                    forbidden = "psycopg" if mode == "local" else "pyodbc"
                    if name == forbidden or name.startswith(forbidden + "."):
                        raise AssertionError("Unused database driver imported")
                    return original_import(name, *args, **kwargs)

                # Dummy values never leave the mocked driver.
                env = {"DB_MODE": mode, "DB_PASSWORD": "unit-test-only", "DATABASE_URL": "unit-test-only"}
                with patch.dict(os.environ, env), patch.dict(sys.modules, modules):
                    with patch("builtins.__import__", side_effect=guarded_import):
                        with patch.object(database, "_ensure_product_availability_column") as ensure:
                            self.assertIs(database.get_connection(), connection)
                if mode == "local":
                    ensure.assert_called_once_with(connection)
                else:
                    ensure.assert_not_called()
                    self.assertIs(driver.connect.call_args.kwargs["row_factory"], rows.namedtuple_row)
                connection.commit.assert_not_called()
                connection.rollback.assert_not_called()

    def test_local_schema_failure_closes_connection(self):
        driver = ModuleType("pyodbc")
        connection = MagicMock()
        driver.connect = MagicMock(return_value=connection)
        with patch.dict(os.environ, {"DB_MODE": "local", "DB_PASSWORD": "unit-test-only"}):
            with patch.dict(sys.modules, {"pyodbc": driver}):
                with patch.object(database, "_ensure_product_availability_column", side_effect=RuntimeError):
                    with self.assertRaises(RuntimeError):
                        database.get_connection()
        connection.close.assert_called_once_with()


def _read_only_availability_check(connection):
    with closing(connection.cursor()) as cursor:
        cursor.execute("SELECT TOP 0 IsAvailable FROM Products")


def run_live_checks():
    failures = 0
    for mode in ("local", "postgres"):
        stage = "connection"
        try:
            with patch.dict(os.environ, {"DB_MODE": mode}):
                with patch.object(database, "_ensure_product_availability_column", _read_only_availability_check):
                    with closing(database.get_connection()) as connection:
                        print(f"{mode}: connection PASS")
                        with closing(connection.cursor()) as cursor:
                            stage = "product count and attribute/index access"
                            database.execute_query(
                                cursor,
                                "SELECT COUNT(*) AS ProductCount FROM Products",
                                'SELECT COUNT(*) AS "ProductCount" FROM "Products"',
                            )
                            row = cursor.fetchone()
                            if row.ProductCount != row[0]:
                                raise AssertionError("Row access mismatch")
                            print(f"{mode}: product count PASS ({row[0]}); attribute/index PASS")
                            stage = "parameterized helper"
                            database.execute_query(
                                cursor,
                                "SELECT CAST(? AS INTEGER) AS ProbeValue",
                                'SELECT CAST(%s AS INTEGER) AS "ProbeValue"',
                                7,
                            )
                            if cursor.fetchone().ProbeValue != 7:
                                raise AssertionError("Parameter value mismatch")
                            print(f"{mode}: parameterized helper PASS")
        except Exception as error:
            failures += 1
            # Driver messages can contain connection details. Print the type only.
            print(f"{mode}: {stage} FAIL ({type(error).__name__}); remaining checks NOT RUN")
    return failures


if __name__ == "__main__":
    if sys.argv[1:] == ["--live"]:
        raise SystemExit(bool(run_live_checks()))
    unittest.main()
