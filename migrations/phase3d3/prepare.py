"""Offline review/SQL preparation only. No database driver, credentials or execution path."""
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import re
from datetime import datetime, timezone
from uuid import UUID

ROOT = Path(__file__).resolve().parent
SQL_ROOT = ROOT.parent / "phase3d1"
DATABASES = {"sqlserver": "BunChaViet_Phase3D3_Test", "postgres": "bunchaviet_phase3d3_test"}


class GuardError(ValueError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def template(backend, action):
    if backend not in DATABASES or action not in ("up", "down"):
        raise GuardError("BCV_INVALID_OPERATION")
    return (SQL_ROOT / f"{backend}_{action}.sql").read_text(encoding="utf-8")


def validate_target(target, observed):
    fields = {"backend", "environment", "server", "port", "database", "role", "test_id"}
    if set(target) != fields or target.get("environment") != "test":
        raise GuardError("BCV_TEST_ONLY")
    backend = target.get("backend")
    if backend not in DATABASES or target.get("database") != DATABASES[backend]:
        raise GuardError("BCV_CURRENT_DATABASES_BLOCKED")
    for field in ("server", "role"):
        value = target[field]
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.\\:\-]{1,128}", value):
            raise GuardError("BCV_INVALID_IDENTITY")
    if type(target["port"]) is not int or not 0 < target["port"] < 65536:
        raise GuardError("BCV_INVALID_PORT")
    if not isinstance(target["test_id"], str) or str(UUID(target["test_id"])) != target["test_id"]:
        raise GuardError("BCV_INVALID_TEST_ID")
    if backend == "postgres":
        try:
            address = ipaddress.ip_address(target["server"])
        except ValueError:
            raise GuardError("BCV_POSTGRES_LITERAL_ADDRESS_REQUIRED") from None
        if not address.is_loopback:
            raise GuardError("BCV_POSTGRES_LOCAL_TEST_ONLY")
    # Observation must come from a separate read-only inspection of the proposed test DB.
    # It is review evidence, not cryptographic attestation; SQL checks the actual DB again.
    if not isinstance(observed, dict) or any(observed.get(k) != v for k, v in target.items()):
        raise GuardError("BCV_OBSERVED_TARGET_MISMATCH")
    if observed.get("marker") != "BunChaViet migration test:" + target["test_id"]:
        raise GuardError("BCV_DATABASE_MARKER_MISMATCH")
    if observed.get("transaction_state") != "IDLE" or observed.get("autocommit") is not True:
        raise GuardError("BCV_NEW_AUTOCOMMIT_CONNECTION_REQUIRED")


def validate_approval(target, action, sql, approval):
    if not isinstance(approval, dict) or approval.get("approved") is not True or approval.get("environment") != "test":
        raise GuardError("BCV_EXPLICIT_APPROVAL_REQUIRED")
    if approval.get("target_sha256") != digest(target) or approval.get("action") != action:
        raise GuardError("BCV_APPROVAL_TARGET_OR_ACTION_MISMATCH")
    if approval.get("template_sha256") != hashlib.sha256(sql.encode()).hexdigest():
        raise GuardError("BCV_TEMPLATE_CHANGED_SINCE_REVIEW")
    for field in ("approval_reference", "backup_restore_reference", "preflight_reference"):
        if not isinstance(approval.get(field), str) or not approval[field].strip():
            raise GuardError("BCV_REVIEW_EVIDENCE_REQUIRED")
    try:
        expires = datetime.fromisoformat(approval["expires_at"])
        valid = expires.tzinfo is not None and expires > datetime.now(timezone.utc)
    except (KeyError, TypeError, ValueError):
        valid = False
    if not valid:
        raise GuardError("BCV_APPROVAL_EXPIRED_OR_INVALID")


def render(target, action, observed, approval):
    validate_target(target, observed)
    sql = template(target["backend"], action)
    validate_approval(target, action, sql, approval)
    replacements = {
        "__TARGET_SERVER__": target["server"],
        "__TARGET_ROLE__": target["role"],
        "__TEST_ID__": target["test_id"],
        "__APPROVAL__": f"BunChaViet phase3d3 test {action} approved",
    }
    for old, new in replacements.items():
        sql = sql.replace(old, new)
    if target["backend"] == "postgres":
        sql = sql.replace("expected_port integer := 0;", f"expected_port integer := {target['port']};")
    else:
        sql = sql.replace("DECLARE @ExpectedPort int = 0;", f"DECLARE @ExpectedPort int = {target['port']};")
    if re.search(r"__[A-Z_]+__", sql):
        raise GuardError("BCV_UNRESOLVED_TEMPLATE")
    return sql


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--observation", type=Path)
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--action", choices=("up", "down"), default="up")
    parser.add_argument("--output", type=Path, help="Write reviewed SQL under phase3d3/prepared; NEVER execute")
    args = parser.parse_args(argv)
    try:
        if args.manifest is None:
            if args.output or args.observation or args.approval:
                raise GuardError("BCV_MANIFEST_REQUIRED")
            print("DRY RUN: offline only; no connection, no SQL execution, no files written.")
            return 0
        target = json.loads(args.manifest.read_text(encoding="utf-8"))
        sql = template(target.get("backend"), args.action)
        if args.observation is None:
            raise GuardError("BCV_OBSERVATION_REQUIRED")
        observed = json.loads(args.observation.read_text(encoding="utf-8"))
        validate_target(target, observed)
        print("target_sha256=" + digest(target))
        print("template_sha256=" + hashlib.sha256(sql.encode()).hexdigest())
        if args.output is None:
            print("DRY RUN: target evidence validated offline; no SQL artifact written or executed.")
            return 0
        if args.approval is None:
            raise GuardError("BCV_APPROVAL_REQUIRED_FOR_ARTIFACT")
        output = args.output.resolve()
        if not output.is_relative_to(ROOT / "prepared") or output.suffix != ".sql":
            raise GuardError("BCV_OUTPUT_MUST_BE_IN_PREPARED_DIRECTORY")
        approval = json.loads(args.approval.read_text(encoding="utf-8"))
        rendered = render(target, args.action, observed, approval)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8", newline="\n") as file:
            file.write(rendered)
        print("Reviewed test SQL artifact written. NOT executed; engine verification still required.")
        return 0
    except (GuardError, ValueError, TypeError, KeyError, OSError, AttributeError):
        # Never echo JSON, connection text, paths or third-party exceptions.
        print("BLOCKED: invalid or incomplete test review evidence. No SQL executed.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
