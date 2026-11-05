
import os
from database import get_connection


def test_database(mode):
    os.environ["DB_MODE"] = mode

    try:
        conn = get_connection()
        cursor = conn.cursor()

        if mode == "postgres":
            cursor.execute(
                'SELECT COUNT(*) FROM "Products"'
            )
        else:
            cursor.execute(
                "SELECT COUNT(*) FROM Products"
            )

        total = cursor.fetchone()[0]

        print(f"{mode}: OK - {total} products")

        cursor.close()
        conn.close()

    except Exception as error:
        print(f"{mode}: ERROR - {error}")


test_database("local")
test_database("postgres")
