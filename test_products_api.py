
import os

from main import app


def test_api(mode):
    os.environ["DB_MODE"] = mode

    with app.test_client() as client:
        response = client.get("/api/products")

        print(f"\nDatabase: {mode}")
        print(f"HTTP status: {response.status_code}")

        if response.status_code == 200:
            products = response.get_json()
            print(f"So san pham: {len(products)}")

            if products:
                print(f"San pham dau tien: {products[0]['name']}")
        else:
            print(response.get_data(as_text=True)[:500])


if __name__ == "__main__":
    test_api("local")
    test_api("postgres")
