import os

from main import app


def test_login(mode):
    os.environ["DB_MODE"] = mode
    app.config["TESTING"] = True
    with app.test_client() as client:
        response = client.post(
            "/api/customer/login",
            json={
                "email": "not-existing-test@example.com",
                "password": "WrongPassword123!",
            },
        )
        print(f"\nDatabase: {mode}")
        print("HTTP status:", response.status_code)
        print("Response:", response.get_json())


if __name__ == "__main__":
    test_login("local")
    test_login("postgres")
