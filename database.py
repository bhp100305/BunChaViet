import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
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

    return connection
