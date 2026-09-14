from flask import Blueprint, jsonify
from database import get_connection


product_bp = Blueprint("product", __name__)


@product_bp.route("/api/products", methods=["GET"])
def get_products():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            ProductID,
            ProductName,
            Description,
            Price,
            Image,
            CategoryID
        FROM Products
        WHERE IsActive = 1
    """)

    rows = cursor.fetchall()

    products = []

    for row in rows:

        products.append({
            "id": row.ProductID,
            "name": row.ProductName,
            "description": row.Description,
            "price": float(row.Price),
            "image": row.Image,
            "category_id": row.CategoryID
        })

    conn.close()

    return jsonify(products)