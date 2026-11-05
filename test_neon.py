
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

def test_neon():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("ERROR: Chua co DATABASE_URL trong .env")
        return

    try:
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        "ProductID",
                        "ProductName",
                        "Price",
                        "IsAvailable"
                    FROM "Products"
                    ORDER BY "ProductID"
                    LIMIT 5
                """)

                products = cursor.fetchall()

                print("Ket noi Neon thanh cong!")
                print("5 san pham dau tien:")

                for product in products:
                    print(
                        f"ID: {product[0]} | "
                        f"Ten: {product[1]} | "
                        f"Gia: {product[2]} | "
                        f"Con ban: {product[3]}"
                    )

    except Exception as error:
        print("Loi:", error)


if __name__ == "__main__":
    test_neon()
