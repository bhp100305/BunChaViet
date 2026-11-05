"""Runtime configuration/OAuth tests: no database, real secrets, or email sends."""

from collections import defaultdict, deque
from contextlib import nullcontext
from datetime import timedelta
from http.cookies import SimpleCookie
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, mock_open, patch

from flask import session
from google.auth.exceptions import RefreshError

import database
from routes import email_otp as otp


MAIN_PATH = Path(__file__).with_name("main.py")
FIXTURE_KEY = "isolated-fixture-key-for-runtime-tests"
FIXTURE_URL = "postgresql://fixture:fixture@db.invalid/fixture?sslmode=require"


class RuntimeEnvironmentTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {"APP_ENV": "local", "DB_MODE": "local", "FLASK_SECRET_KEY": FIXTURE_KEY}, clear=True)
        env.start()
        self.addCleanup(env.stop)
        for name in ("_email_send_log", "_ip_send_log"):
            replacement = patch.object(otp, name, defaultdict(deque))
            replacement.start()
            self.addCleanup(replacement.stop)

    def production(self):
        os.environ.update(APP_ENV="production", DB_MODE="postgres", DATABASE_URL=FIXTURE_URL)

    def load_main(self, credentials=None, mock_oauth=True):
        spec = importlib.util.spec_from_file_location("runtime_environment_main", MAIN_PATH)
        module = importlib.util.module_from_spec(spec)
        if credentials is None:
            credentials = MagicMock(refresh_token="isolated-fixture-refresh")
        oauth = patch.object(otp, "_read_gmail_credentials", return_value=credentials) if mock_oauth else nullcontext()
        with patch.dict(sys.modules, {spec.name: module}), oauth, patch.object(database, "get_connection", side_effect=AssertionError("Startup must not connect to DB")):
            spec.loader.exec_module(module)
        return module

    def test_production_detection(self):
        self.assertFalse(database.is_production())
        os.environ["DB_MODE"] = "postgres"
        self.assertFalse(database.is_production())
        os.environ["APP_ENV"] = "production"
        self.assertTrue(database.is_production())
        os.environ.update(APP_ENV="local", RENDER="true")
        self.assertTrue(database.is_production())

    def test_render_import_does_not_load_dotenv(self):
        os.environ["RENDER"] = "true"
        spec = importlib.util.spec_from_file_location("runtime_environment_database", Path(database.__file__))
        module = importlib.util.module_from_spec(spec)
        with patch("dotenv.load_dotenv") as load:
            spec.loader.exec_module(module)
        load.assert_not_called()

    def test_local_import_keeps_dotenv(self):
        spec = importlib.util.spec_from_file_location("runtime_environment_database", Path(database.__file__))
        module = importlib.util.module_from_spec(spec)
        with patch("dotenv.load_dotenv") as load:
            spec.loader.exec_module(module)
        load.assert_called_once()

    def test_local_starts_without_database_or_gmail(self):
        module = self.load_main()
        self.assertEqual(module.app.test_client().get("/").status_code, 200)
        self.assertFalse(module.app.config["SESSION_COOKIE_SECURE"])
        self.assertEqual(module.app.config["PERMANENT_SESSION_LIFETIME"], timedelta(days=30))

    def test_local_reads_existing_secret_file(self):
        os.environ.pop("FLASK_SECRET_KEY")
        opener = mock_open(read_data="isolated-local-file-key")
        with patch("builtins.open", opener):
            module = self.load_main()
        self.assertEqual(module.app.secret_key, "isolated-local-file-key")
        opener().write.assert_not_called()

    def test_local_generates_missing_secret_only_in_mock_file(self):
        os.environ.pop("FLASK_SECRET_KEY")
        opener = mock_open()
        opener.side_effect = [FileNotFoundError(), opener.return_value]
        with patch("builtins.open", opener), patch("secrets.token_urlsafe", return_value="isolated-generated-fixture-key"):
            module = self.load_main()
        self.assertEqual(module.app.secret_key, "isolated-generated-fixture-key")
        opener.return_value.write.assert_called_once_with("isolated-generated-fixture-key")

    def test_production_missing_or_blank_secret_never_reads_file(self):
        self.production()
        for value in (None, "", "  "):
            if value is None:
                os.environ.pop("FLASK_SECRET_KEY", None)
            else:
                os.environ["FLASK_SECRET_KEY"] = value
            with patch("builtins.open") as opener:
                with self.assertRaisesRegex(RuntimeError, "FLASK_SECRET_KEY"):
                    self.load_main()
            opener.assert_not_called()

    def test_production_valid_configuration(self):
        self.production()
        with patch("builtins.open") as opener:
            module = self.load_main()
        self.assertEqual(module.app.secret_key, FIXTURE_KEY)
        self.assertEqual(module.app.test_client().get("/", base_url="https://fixture.example").status_code, 200)
        opener.assert_not_called()

    def test_render_flag_enforces_production(self):
        os.environ.update(RENDER="true", DB_MODE="postgres", DATABASE_URL=FIXTURE_URL)
        os.environ.pop("FLASK_SECRET_KEY")
        with self.assertRaisesRegex(RuntimeError, "FLASK_SECRET_KEY"):
            self.load_main()

    def test_production_database_validation(self):
        self.production()
        for key, value, message in (("DB_MODE", "local", "DB_MODE"), ("DATABASE_URL", "", "DATABASE_URL"), ("DATABASE_URL", "sensitive-fixture-value", "DATABASE_URL"), ("DATABASE_URL", "postgresql://fixture@db.invalid/fixture", "TLS"), ("DATABASE_URL", "postgresql://fixture@db.invalid:invalid/fixture?sslmode=require", "DATABASE_URL")):
            with patch.dict(os.environ, {key: value}):
                with self.assertRaisesRegex(RuntimeError, message) as raised:
                    self.load_main()
                self.assertNotIn("sensitive-fixture-value", str(raised.exception))

    def test_invalid_db_mode_does_not_echo_value(self):
        self.production()
        os.environ["DB_MODE"] = "sensitive-fixture-value"
        with self.assertRaises(ValueError) as raised:
            self.load_main()
        self.assertNotIn("sensitive-fixture-value", str(raised.exception))

    def test_optional_otp_secret_and_blank_override(self):
        self.production()
        module = self.load_main()
        with module.app.app_context():
            self.assertEqual(otp.get_otp_secret(), FIXTURE_KEY)
        os.environ["OTP_HMAC_SECRET"] = "isolated-otp-fixture-key"
        module = self.load_main()
        with module.app.app_context():
            self.assertEqual(otp.get_otp_secret(), "isolated-otp-fixture-key")
        os.environ["OTP_HMAC_SECRET"] = " "
        with self.assertRaisesRegex(RuntimeError, "OTP_HMAC_SECRET"):
            self.load_main()

    def test_cookie_attributes(self):
        for production in (False, True):
            with self.subTest(production=production):
                if production:
                    self.production()
                module = self.load_main()
                def set_fixture_session():
                    session["fixture"] = True
                    return "ok"
                module.app.add_url_rule("/_fixture_session", view_func=set_fixture_session)
                response = module.app.test_client().get("/_fixture_session", base_url="https://fixture.example" if production else "http://localhost")
                cookie = SimpleCookie()
                cookie.load(response.headers["Set-Cookie"])
                morsel = cookie[module.app.config["SESSION_COOKIE_NAME"]]
                self.assertEqual(bool(morsel["secure"]), production)
                self.assertTrue(morsel["httponly"])
                self.assertEqual(morsel["samesite"], "Lax")

    def test_linux_oauth_paths(self):
        with patch.object(otp.platform, "system", return_value="Linux"), patch.object(otp.Path, "home", return_value=Path("/home/fixture")):
            self.assertEqual(otp.get_gmail_token_path(), Path.home() / ".config" / "bunchaviet" / "gmail_token.json")
            self.production()
            self.assertEqual(otp.get_gmail_token_path().as_posix(), "/etc/secrets/gmail_token.json")
            for invalid in (r"C:\private\gmail_token.json", "relative-token.json"):
                os.environ["GMAIL_TOKEN_PATH"] = invalid
                with self.assertRaises(RuntimeError):
                    otp.get_gmail_token_path()

    def test_windows_local_oauth_path_preserved(self):
        with patch.object(otp.platform, "system", return_value="Windows"):
            self.assertEqual(otp.get_gmail_token_path(), otp.DEFAULT_GMAIL_TOKEN_PATH)

    def test_missing_oauth_file(self):
        with patch.object(otp.Path, "is_file", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "GMAIL_TOKEN_PATH"):
                otp._read_gmail_credentials()

    def test_production_missing_oauth_file_rejects_startup(self):
        self.production()
        with patch.object(otp.Path, "is_file", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "GMAIL_TOKEN_PATH"):
                self.load_main(mock_oauth=False)

    def test_unreadable_or_invalid_oauth_file_is_redacted(self):
        for error in (PermissionError("sensitive-fixture-value"), ValueError("sensitive-fixture-value")):
            with patch.object(otp.Path, "is_file", return_value=True), patch.object(otp.Credentials, "from_authorized_user_file", side_effect=error):
                with self.assertRaisesRegex(RuntimeError, "GMAIL_TOKEN_PATH") as raised:
                    otp._read_gmail_credentials()
            self.assertNotIn("sensitive-fixture-value", str(raised.exception))

    def test_production_requires_refresh_credentials(self):
        self.production()
        with self.assertRaisesRegex(RuntimeError, "refresh token"):
            self.load_main(MagicMock(refresh_token=None))

    def test_production_rejects_missing_oauth_client_credentials(self):
        self.production()
        for missing in ("client_id", "client_secret"):
            credentials = MagicMock(refresh_token="isolated-refresh", client_id="isolated-client", client_secret="isolated-client-secret")
            setattr(credentials, missing, "")
            with self.assertRaisesRegex(RuntimeError, "client credentials"):
                self.load_main(credentials)

    def test_sender_validation_is_redacted(self):
        self.production()
        os.environ["GMAIL_ADDRESS"] = "sensitive-fixture-value"
        with self.assertRaisesRegex(RuntimeError, "GMAIL_ADDRESS") as raised:
            self.load_main()
        self.assertNotIn("sensitive-fixture-value", str(raised.exception))

    def test_valid_access_token_does_not_refresh_or_write(self):
        credentials = MagicMock(valid=True)
        with patch.object(otp, "_read_gmail_credentials", return_value=credentials), patch.object(otp.Path, "write_text") as write:
            self.assertIs(otp.load_gmail_credentials(), credentials)
        credentials.refresh.assert_not_called()
        write.assert_not_called()

    def test_expired_token_refreshes_in_memory_on_read_only_mount(self):
        credentials = MagicMock(valid=False, expired=True, refresh_token="isolated-fixture-refresh")
        credentials.refresh.side_effect = lambda request: setattr(credentials, "valid", True)
        with patch.object(otp.Path, "is_file", return_value=True), patch.object(otp.Credentials, "from_authorized_user_file", return_value=credentials), patch.object(otp.Path, "write_text", side_effect=PermissionError("read-only fixture")) as write, patch.object(otp, "Request") as transport:
            self.assertIs(otp.load_gmail_credentials(), credentials)
        credentials.refresh.assert_called_once_with(transport.return_value)
        credentials.to_json.assert_not_called()
        write.assert_not_called()

    def test_refresh_failure_is_redacted(self):
        credentials = MagicMock(valid=False, refresh_token="isolated-fixture-refresh")
        credentials.refresh.side_effect = RefreshError("sensitive-fixture-value")
        with patch.object(otp, "_read_gmail_credentials", return_value=credentials), patch.object(otp, "Request"):
            with self.assertRaisesRegex(RuntimeError, "refresh failed") as raised:
                otp.load_gmail_credentials()
        self.assertNotIn("sensitive-fixture-value", str(raised.exception))

    def test_invalid_unrefreshable_token(self):
        credentials = MagicMock(valid=False, refresh_token=None)
        with patch.object(otp, "_read_gmail_credentials", return_value=credentials):
            with self.assertRaises(RuntimeError):
                otp.load_gmail_credentials()
        credentials.refresh.assert_not_called()

    def test_otp_send_verify_cooldown_and_constants(self):
        module = self.load_main()
        client = module.app.test_client()
        with patch.object(otp, "send_gmail_otp") as send:
            response = client.post("/api/email-otp/send", json={"email": "fixture@example.com"})
            self.assertEqual(response.status_code, 200)
            code = send.call_args.args[1]
            self.assertEqual(response.json["expiresIn"], 300)
            self.assertEqual(response.json["resendAfter"], 60)
            self.assertEqual(client.post("/api/email-otp/send", json={"email": "fixture@example.com"}).status_code, 429)
            self.assertEqual(client.post("/api/email-otp/verify", json={"email": "fixture@example.com", "otp": code}).status_code, 200)
        with client.session_transaction() as saved:
            self.assertEqual(saved["checkout_verified_email"], "fixture@example.com")
        self.assertEqual(otp.OTP_VERIFY_SESSION_SECONDS, 900)
        self.assertEqual(otp.OTP_MAX_ATTEMPTS, 5)
        self.assertEqual(otp.MAX_SENDS_PER_EMAIL, 3)
        self.assertEqual(otp.MAX_SENDS_PER_IP, 10)

    def test_otp_failure_does_not_log_sensitive_error(self):
        module = self.load_main()
        with patch.object(otp, "send_gmail_otp", side_effect=RefreshError("sensitive-fixture-value")), patch.object(module.app, "logger") as logger:
            response = module.app.test_client().post("/api/email-otp/send", json={"email": "fixture@example.com"})
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("sensitive-fixture-value", response.get_data(as_text=True))
        self.assertNotIn("sensitive-fixture-value", str(logger.mock_calls))

    def test_otp_expiry_and_attempt_limit(self):
        module = self.load_main()
        for expired in (False, True):
            client = module.app.test_client()
            with patch.object(otp, "send_gmail_otp") as send, patch.object(otp.time, "time", return_value=1_800_000_000):
                self.assertEqual(client.post("/api/email-otp/send", json={"email": "expiry-fixture@example.com"}).status_code, 200)
                code = send.call_args.args[1]
            if expired:
                with patch.object(otp.time, "time", return_value=1_800_000_301):
                    self.assertEqual(client.post("/api/email-otp/verify", json={"email": "expiry-fixture@example.com", "otp": code}).status_code, 400)
            else:
                incorrect = "000000" if code != "000000" else "111111"
                with patch.object(otp.time, "time", return_value=1_800_000_001):
                    for _ in range(5):
                        self.assertEqual(client.post("/api/email-otp/verify", json={"email": "expiry-fixture@example.com", "otp": incorrect}).status_code, 400)
                    self.assertEqual(client.post("/api/email-otp/verify", json={"email": "expiry-fixture@example.com", "otp": code}).status_code, 429)

    def test_otp_email_send_limit(self):
        module = self.load_main()
        with patch.object(otp, "send_gmail_otp") as send:
            for _ in range(3):
                response = module.app.test_client().post("/api/email-otp/send", json={"email": "rate-fixture@example.com"})
                self.assertEqual(response.status_code, 200)
            self.assertEqual(module.app.test_client().post("/api/email-otp/send", json={"email": "rate-fixture@example.com"}).status_code, 429)
        self.assertEqual(send.call_count, 3)

    def test_otp_ip_send_limit(self):
        module = self.load_main()
        with patch.object(otp, "send_gmail_otp") as send:
            for index in range(10):
                response = module.app.test_client().post("/api/email-otp/send", json={"email": f"ip-fixture-{index}@example.com"})
                self.assertEqual(response.status_code, 200)
            response = module.app.test_client().post("/api/email-otp/send", json={"email": "ip-fixture-final@example.com"})
            self.assertEqual(response.status_code, 429)
        self.assertEqual(send.call_count, 10)


if __name__ == "__main__":
    unittest.main()
