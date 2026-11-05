from flask import Blueprint, jsonify
from database import get_connection


product_bp = Blueprint("product", __name__)


@product_bp.route("/api/products", methods=["GET"])
def get_products():


    conn = get_connection()

    try:
        cursor = conn.cursor()

        query = """
                SELECT
                    ProductID,
                    ProductName,
                    Description,
                    Price,
                    Image,
                    CategoryID,
                    IsAvailable
                FROM Products
                WHERE IsActive = 1
                ORDER BY ProductID
            """

        cursor.execute(query)
        rows = cursor.fetchall()

        products = []

        for row in rows:
            products.append({
                "id": row.ProductID,
                "name": row.ProductName,
                "description": row.Description,
                "price": float(row.Price),
                "image": row.Image,
                "category_id": row.CategoryID,
                "isAvailable": bool(row.IsAvailable),
            })

        cursor.close()

        return jsonify(products)

    finally:
        conn.close()
