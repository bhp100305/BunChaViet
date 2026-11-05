"""Offline guard contract tests. No database connections or DDL."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import tempfile
import unittest
from unittest.mock import Mock

import prepare


class Guards(unittest.TestCase):
    def fixture(self, backend="postgres", action="up"):
        target = dict(backend=backend, environment="test", server="127.0.0.1",
                      port=5432 if backend == "postgres" else 1433,
                      database=prepare.DATABASES[backend], role="migration_test",
                      test_id="12345678-1234-1234-1234-123456789abc")
        observed = dict(target, marker="BunChaViet migration test:" + target["test_id"],
                        transaction_state="IDLE", autocommit=True)
        approval = dict(approved=True, environment="test", action=action,
                        target_sha256=prepare.digest(target),
                        template_sha256=hashlib.sha256(prepare.template(backend, action).encode()).hexdigest(),
                        approval_reference="mock-approval", backup_restore_reference="mock-restore",
                        preflight_reference="mock-preflight",
                        expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat())
        return target, observed, approval

    def test_render_both_backends_and_directions(self):
        for backend in prepare.DATABASES:
            for action in ("up", "down"):
                with self.subTest(backend=backend, action=action):
                    target, observed, approval = self.fixture(backend, action)
                    sql = prepare.render(target, action, observed, approval)
                    self.assertNotIn("__APPROVAL__", sql)
                    self.assertIn(f"test {action} approved", sql)

    def test_mocked_target_drift_fails_before_dispatch(self):
        for backend in prepare.DATABASES:
            for field, bad in (("database", "BunCha"), ("server", "other"),
                               ("role", "other"), ("marker", None),
                               ("transaction_state", "INTRANS"), ("autocommit", False)):
                with self.subTest(backend=backend, field=field):
                    target, observed, approval = self.fixture(backend)
                    mock_connection = Mock()
                    observed[field] = bad
                    mock_connection.inspect.return_value = observed
                    with self.assertRaises(prepare.GuardError):
                        sql = prepare.render(target, "up", mock_connection.inspect(), approval)
                        mock_connection.execute(sql)
                    mock_connection.execute.assert_not_called()
                    mock_connection.commit.assert_not_called()
                    mock_connection.rollback.assert_not_called()

    def test_production_and_current_names_blocked_even_with_matching_observation(self):
        for backend in prepare.DATABASES:
            for field, value in (("environment", "production"), ("database", "BunCha"),
                                 ("database", "neondb")):
                target, observed, approval = self.fixture(backend)
                target[field] = observed[field] = value
                approval["target_sha256"] = prepare.digest(target)
                with self.assertRaises(prepare.GuardError):
                    prepare.render(target, "up", observed, approval)

    def test_missing_null_false_wrong_and_expired_approval(self):
        for field, value in (("approved", None), ("approved", False), ("approved", "true"),
                             ("action", "down"), ("environment", "production"),
                             ("target_sha256", "wrong"), ("template_sha256", "wrong"),
                             ("backup_restore_reference", ""), ("preflight_reference", None),
                             ("expires_at", "2020-01-01T00:00:00+00:00")):
            with self.subTest(field=field, value=value):
                target, observed, approval = self.fixture()
                approval[field] = value
                with self.assertRaises(prepare.GuardError):
                    prepare.render(target, "up", observed, approval)

    def test_injection_and_remote_postgres_blocked(self):
        for field, value in (("server", "x';SELECT 1;--"), ("role", "x'"),
                             ("server", "192.0.2.1"), ("test_id", "invalid")):
            target, observed, approval = self.fixture()
            target[field] = observed[field] = value
            with self.assertRaises(ValueError):
                prepare.render(target, "up", observed, approval)

    def test_default_cli_cannot_dispatch(self):
        self.assertEqual(prepare.main([]), 0)

    def test_dry_run_and_output_approval_boundary(self):
        target, observed, _ = self.fixture()
        with tempfile.TemporaryDirectory(dir=prepare.ROOT) as folder:
            from pathlib import Path
            root = Path(folder)
            manifest = root / "manifest.json"
            observation = root / "observation.json"
            manifest.write_text(json.dumps(target), encoding="utf-8")
            observation.write_text(json.dumps(observed), encoding="utf-8")
            args = ["--manifest", str(manifest), "--observation", str(observation)]
            self.assertEqual(prepare.main(args), 0)
            output = prepare.ROOT / "prepared" / "should_never_exist.sql"
            self.assertEqual(prepare.main(args + ["--output", str(output)]), 2)
            self.assertFalse(output.exists())

    def test_stale_approval_rejects_changed_script(self):
        target, observed, approval = self.fixture()
        with unittest.mock.patch.object(prepare, "template", return_value=prepare.template("postgres", "up") + "\n-- changed\n"):
            with self.assertRaisesRegex(prepare.GuardError, "BCV_TEMPLATE_CHANGED"):
                prepare.render(target, "up", observed, approval)

    def test_sql_transaction_and_ownership_contract(self):
        for backend in prepare.DATABASES:
            down = prepare.template(backend, "down")
            self.assertLess(down.index("BCV_INDEX_DEFINITION_OR_OWNER_DRIFT"), down.index("DROP INDEX"))
            self.assertIn("phase3d3:OrderCode:v1", down)
            self.assertNotIn("CASCADE", down)
        ss = prepare.template("sqlserver", "up")
        self.assertLess(ss.index("@@TRANCOUNT"), ss.index("BEGIN TRANSACTION"))
        pg = prepare.template("postgres", "up")
        self.assertLess(pg.index("COMMIT;"), pg.index("LOCK TABLE"))
        self.assertNotIn("BEGIN;", pg)

    def test_sql_whitespace_and_scope(self):
        for file in prepare.SQL_ROOT.glob("*.sql"):
            text = file.read_text(encoding="utf-8")
            self.assertTrue(text.endswith("\n"), file.name)
            self.assertFalse(any(line.rstrip() != line for line in text.splitlines()), file.name)
            self.assertNotRegex(text, r"(?im)^\s*(INSERT\s|UPDATE\s|DELETE\s|TRUNCATE\s|USE\s)")


if __name__ == "__main__":
    unittest.main()
