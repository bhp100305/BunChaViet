import pyodbc
import threading


_product_schema_lock = threading.Lock()
_product_schema_ready = False


def _ensure_product_availability_column(connection):
    """Add the availability flag once for existing SQL Server databases."""
    global _product_schema_ready
    if _product_schema_ready:
        return

    with _product_schema_lock:
        if _product_schema_ready:
            return

        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                IF COL_LENGTH('dbo.Products', 'IsAvailable') IS NULL
                BEGIN
                    ALTER TABLE dbo.Products
                    ADD IsAvailable bit NOT NULL
                        CONSTRAINT DF_Products_IsAvailable DEFAULT (1) WITH VALUES
                END
                """
            )
            connection.commit()
            _product_schema_ready = True
        finally:
            cursor.close()

def get_connection():

    connection = pyodbc.connect(
        "DRIVER={SQL Server};SERVER=127.0.0.1;DATABASE=BunCha;;UID=sa;PWD=HuyPhu@999;TrustServerCertificate=yes;MARS_Connection=yes;"
    )

    try:
        _ensure_product_availability_column(connection)
    except Exception:
        connection.close()
        raise

    return connection
