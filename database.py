
import os
import threading
from urllib.parse import parse_qs, urlsplit

from dotenv import load_dotenv


def is_production():
    """Render's runtime flag cannot be disabled by a local APP_ENV value."""
    return (
        os.getenv("RENDER", "").strip().lower() == "true"
        or os.getenv("APP_ENV", "").strip().lower() == "production"
    )


if not is_production():
    load_dotenv()

_product_schema_lock = threading.Lock()
_product_schema_ready = False


def _ensure_product_availability_column(connection):
    """Chỉ áp dụng cho SQL Server Local."""
    global _product_schema_ready

    if _product_schema_ready:
        return

    with _product_schema_lock:
        if _product_schema_ready:
            return

        cursor = connection.cursor()

        try:
            cursor.execute("""
                IF COL_LENGTH('dbo.Products', 'IsAvailable') IS NULL
                BEGIN
                    ALTER TABLE dbo.Products
                    ADD IsAvailable BIT NOT NULL
                        CONSTRAINT DF_Products_IsAvailable
                        DEFAULT (1) WITH VALUES
                END
            """)

            connection.commit()
            _product_schema_ready = True

        finally:
            cursor.close()


def get_db_mode():
    """Return the configured backend, defaulting to SQL Server Local."""
    db_mode = os.getenv("DB_MODE", "local").strip().lower()
    if db_mode not in ("local", "postgres"):
        raise ValueError("DB_MODE must be 'local' or 'postgres'.")
    return db_mode


def validate_production_database():
    """Validate configuration without importing a driver or connecting."""
    if get_db_mode() != "postgres":
        raise RuntimeError("Production requires DB_MODE=postgres.")
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("Production requires DATABASE_URL.")
    try:
        parsed = urlsplit(database_url)
        valid_url = (
            parsed.scheme in ("postgres", "postgresql")
            and bool(parsed.hostname)
            and bool(parsed.path.strip("/"))
            and (parsed.port is None or 0 < parsed.port <= 65535)
        )
        secure = parse_qs(parsed.query).get("sslmode", [""])[-1] in (
            "require", "verify-ca", "verify-full",
        )
    except ValueError:
        raise RuntimeError("DATABASE_URL must be a valid PostgreSQL URL.") from None
    if not valid_url:
        raise RuntimeError("DATABASE_URL must be a valid PostgreSQL URL.")
    if not secure:
        raise RuntimeError("DATABASE_URL must require TLS using sslmode.")


def execute_query(cursor, sql_server, postgres, *params):
    """Execute explicit dialect SQL with positional values; leave transactions to callers.

    Pass values as separate arguments, including a single list/tuple value when
    that is itself a database parameter. SQL is never rewritten.
    """
    query = postgres if get_db_mode() == "postgres" else sql_server
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)
    return cursor


def get_connection():
    db_mode = get_db_mode()

    if db_mode == "postgres":
        import psycopg
        from psycopg.rows import namedtuple_row

        database_url = os.getenv("DATABASE_URL", "").strip()

        if not database_url:
            raise RuntimeError(
                "Chua cau hinh DATABASE_URL"
            )

        return psycopg.connect(
            database_url,
            row_factory=namedtuple_row,
            connect_timeout=30
        )

    if db_mode == "local":
        import pyodbc

        server = os.getenv("DB_SERVER", "127.0.0.1")
        database = os.getenv("DB_NAME", "BunCha")
        username = os.getenv("DB_USER", "sa")
        password = os.getenv("DB_PASSWORD")
        driver = os.getenv(
            "DB_DRIVER",
            "ODBC Driver 17 for SQL Server"
        )

        if not password:
            raise RuntimeError(
                "Chua cau hinh DB_PASSWORD"
            )

        connection_string = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            "Encrypt=yes;"
            "TrustServerCertificate=yes;"
            "MARS_Connection=yes;"
            "Connection Timeout=30;"
        )

        connection = pyodbc.connect(
            connection_string
        )

        try:
            _ensure_product_availability_column(
                connection
            )
        except Exception:
            connection.close()
            raise

        return connection

    raise ValueError(
        f"DB_MODE khong hop le: {db_mode}"
    )
