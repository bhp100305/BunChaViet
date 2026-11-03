from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from database import get_connection


admin_products_bp = Blueprint("admin_products", __name__, url_prefix="/admin")
UPLOAD_FOLDER = "static/images"


def check_admin() -> bool:
    return session.get("role") == "Admin"

# PRODUCTS
# =========================================================

@admin_products_bp.route("/products")
def products() -> Any:
    """Hiển thị danh sách sản phẩm."""

    if not check_admin():
        return redirect(
            url_for("login")
        )

    product_view = request.args.get("view", "active")
    if product_view not in {"active", "archived"}:
        product_view = "active"

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            SELECT
                p.ProductID,
                p.ProductName,
                p.Description,
                p.Price,
                p.Image,
                p.CategoryID,
                c.CategoryName,
                p.IsAvailable

            FROM Products p

            LEFT JOIN Categories c
                ON p.CategoryID = c.CategoryID

            WHERE p.IsActive = ?

            ORDER BY p.ProductID DESC
            """,
            (0 if product_view == "archived" else 1,),
        )

        product_rows = (
            cursor.fetchall()
        )


        cursor.execute(
            """
            SELECT
                CategoryID,
                CategoryName

            FROM Categories

            ORDER BY CategoryName
            """
        )

        category_rows = (
            cursor.fetchall()
        )

    finally:

        cursor.close()
        conn.close()


    return render_template(
        "admin/products.html",

        products=product_rows,

        categories=category_rows,
        product_view=product_view,
    )


# =========================================================
# ADD PRODUCT
# =========================================================

# =========================================================
# ADD PRODUCT - VALIDATION + DUPLICATE CHECK
# =========================================================

@admin_products_bp.route("/products/add", methods=["POST"])
def add_product() -> Any:
    """Thêm sản phẩm mới, kiểm tra dữ liệu và chống trùng."""

    # 1. Kiểm tra quyền Admin
    if not check_admin():
        return jsonify({
            "success": False,
            "message": "Không có quyền thực hiện thao tác này."
        }), 403

    # 2. Nhận dữ liệu từ form
    name = (request.form.get("name") or "").strip()
    description = (request.form.get("description") or "").strip()
    price_raw = (request.form.get("price") or "").strip()
    category_raw = (request.form.get("category") or "").strip()
    image = request.files.get("image")

    # 3. Kiểm tra các trường bắt buộc
    if not name or not price_raw or not category_raw:
        return jsonify({
            "success": False,
            "message": "Vui lòng nhập đầy đủ tên, giá và danh mục."
        }), 400

    # 4. Kiểm tra giá hợp lệ
    try:
        price = Decimal(price_raw)

        if not price.is_finite() or price <= 0:
            raise ValueError("Invalid price")

    except (InvalidOperation, ValueError):
        return jsonify({
            "success": False,
            "message": "Giá sản phẩm phải là số lớn hơn 0."
        }), 400

    # 5. Kiểm tra CategoryID hợp lệ
    try:
        category_id = int(category_raw)

        if category_id <= 0:
            raise ValueError("Invalid category")

    except ValueError:
        return jsonify({
            "success": False,
            "message": "Danh mục sản phẩm không hợp lệ."
        }), 400

    # 6. Kiểm tra phần mở rộng ảnh
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    extension = ""

    if image and image.filename:
        safe_name = secure_filename(image.filename)
        extension = os.path.splitext(safe_name)[1].lower()

        if not safe_name or extension not in allowed_extensions:
            return jsonify({
                "success": False,
                "message": (
                    "Ảnh chỉ được sử dụng định dạng "
                    "JPG, JPEG, PNG hoặc WEBP."
                )
            }), 400

    conn = get_connection()
    cursor = conn.cursor()

    saved_path = None

    try:
        # 7. Kiểm tra danh mục có tồn tại không
        cursor.execute("""
            SELECT CategoryID
            FROM Categories
            WHERE CategoryID = ?
        """, (category_id,))

        if not cursor.fetchone():
            conn.rollback()
            return jsonify({
                "success": False,
                "message": "Danh mục không tồn tại."
            }), 400

        # 8. Kiểm tra tên sản phẩm trùng
        cursor.execute("""
            SELECT
                ProductID,
                IsActive
            FROM Products WITH (UPDLOCK, HOLDLOCK)
            WHERE CategoryID = ?
              AND LOWER(LTRIM(RTRIM(ProductName))) = LOWER(?)
        """, (category_id, name))

        existing_product = cursor.fetchone()

        if existing_product:
            conn.rollback()

            if existing_product[1] == 1:
                message = (
                    "Sản phẩm bị trùng tên "
                    "trong danh mục."
                )
            else:
                message = (
                    "Tên sản phẩm bị trùng với món đang được lưu trữ. "
                    "Hãy khôi phục sản phẩm cũ thay vì thêm mới."
                )

            return jsonify({
                "success": False,
                "message": message
            }), 409

        # 9. Lưu ảnh nếu Admin có tải lên
        filename = ""

        if image and image.filename:
            filename = f"{uuid4().hex}{extension}"

            os.makedirs(
                UPLOAD_FOLDER,
                exist_ok=True
            )

            saved_path = os.path.join(
                UPLOAD_FOLDER,
                filename
            )

            image.save(saved_path)

        # 10. Thêm sản phẩm vào database
        cursor.execute("""
            INSERT INTO Products
            (
                ProductName,
                Description,
                Price,
                Image,
                CategoryID,
                IsActive
            )
            VALUES (?, ?, ?, ?, ?, 1)
        """, (
            name,
            description,
            price,
            filename,
            category_id
        ))

        # 11. Xác nhận lưu vào database
        conn.commit()

        return jsonify({
            "success": True,
            "message": "Thêm sản phẩm thành công."
        }), 201

    except Exception:
        conn.rollback()

        # Xóa ảnh mới nếu quá trình lưu bị lỗi
        if saved_path and os.path.exists(saved_path):
            try:
                os.remove(saved_path)
            except OSError:
                current_app.logger.exception(
                    "Không thể xóa ảnh upload lỗi."
                )

        current_app.logger.exception(
            "Lỗi khi thêm sản phẩm."
        )

        return jsonify({
            "success": False,
            "message": "Không thể thêm sản phẩm. Vui lòng thử lại."
        }), 500

    finally:
        cursor.close()
        conn.close()


# =========================================================
# UPDATE PRODUCT
# =========================================================

@admin_products_bp.route(
    "/products/edit/<int:id>",
    methods=["POST"],
)
def update_product(
    id: int,
) -> Any:
    """Cập nhật sản phẩm."""

    if not check_admin():

        return jsonify({
            "success": False,
            "message": "Không có quyền.",
        }), 403


    name = (
        request.form.get("name")
        or ""
    ).strip()


    description = (
        request.form.get("description")
        or ""
    ).strip()


    price = (
        request.form.get("price")
        or ""
    ).strip()


    category = (
        request.form.get("category")
        or ""
    ).strip()


    if (
        not name
        or
        not price
        or
        not category
    ):

        return jsonify({
            "success": False,

            "message":
                "Vui lòng nhập đầy đủ tên, giá và danh mục.",
        }), 400


    image = request.files.get(
        "image"
    )


    conn = get_connection()
    cursor = conn.cursor()


    try:

        if (
            image
            and
            image.filename
        ):

            filename = secure_filename(
                image.filename
            )


            os.makedirs(
                UPLOAD_FOLDER,
                exist_ok=True,
            )


            image.save(
                os.path.join(
                    UPLOAD_FOLDER,
                    filename,
                )
            )


            cursor.execute(
                """
                UPDATE Products

                SET
                    ProductName = ?,
                    Description = ?,
                    Price = ?,
                    CategoryID = ?,
                    Image = ?

                WHERE ProductID = ?
                """,
                (
                    name,
                    description,
                    price,
                    category,
                    filename,
                    id,
                ),
            )

        else:

            cursor.execute(
                """
                UPDATE Products

                SET
                    ProductName = ?,
                    Description = ?,
                    Price = ?,
                    CategoryID = ?

                WHERE ProductID = ?
                """,
                (
                    name,
                    description,
                    price,
                    category,
                    id,
                ),
            )


        conn.commit()

    finally:

        cursor.close()
        conn.close()


    return jsonify({
        "success": True,
    })


# =========================================================
# ARCHIVE PRODUCT
# =========================================================

@admin_products_bp.route(
    "/products/availability/<int:id>",
    methods=["POST"],
)
def set_product_availability(id: int) -> Any:
    if not check_admin():
        return jsonify({"success": False, "message": "Không có quyền."}), 403

    data = request.get_json(silent=True) or {}
    is_available = data.get("isAvailable")
    if not isinstance(is_available, bool):
        return jsonify({"success": False, "message": "Trạng thái tồn kho không hợp lệ."}), 400

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE Products SET IsAvailable = ? WHERE ProductID = ? AND IsActive = 1",
            (1 if is_available else 0, id),
        )
        if cursor.rowcount == 0:
            conn.rollback()
            return jsonify({"success": False, "message": "Không tìm thấy món đang hoạt động."}), 404
        conn.commit()
        return jsonify({"success": True})
    finally:
        cursor.close()
        conn.close()


@admin_products_bp.route(
    "/products/archive/<int:id>",
    methods=["POST"],
)
def archive_product(id: int) -> Any:
    if not check_admin():
        return jsonify({"success": False, "message": "Không có quyền."}), 403

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Products SET IsActive = 0 WHERE ProductID = ?", (id,))
        if cursor.rowcount == 0:
            conn.rollback()
            return jsonify({"success": False, "message": "Không tìm thấy món ăn."}), 404
        conn.commit()
        return jsonify({"success": True})
    finally:
        cursor.close()
        conn.close()


@admin_products_bp.route(
    "/products/restore/<int:id>",
    methods=["POST"],
)
def restore_product(id: int) -> Any:
    if not check_admin():
        return jsonify({"success": False, "message": "Không có quyền."}), 403

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Products SET IsActive = 1 WHERE ProductID = ?", (id,))
        if cursor.rowcount == 0:
            conn.rollback()
            return jsonify({"success": False, "message": "Không tìm thấy món trong kho lưu trữ."}), 404
        conn.commit()
        return jsonify({"success": True})
    finally:
        cursor.close()
        conn.close()


# DELETE PRODUCT (legacy soft-delete URL)
# =========================================================

@admin_products_bp.route(
    "/products/delete/<int:id>",
    methods=["DELETE"],
)
def delete_product(
    id: int,
) -> Any:
    """Ẩn sản phẩm thay vì xóa vật lý."""

    if not check_admin():

        return jsonify({
            "success": False,
            "message": "Không có quyền.",
        }), 403


    conn = get_connection()
    cursor = conn.cursor()


    try:

        cursor.execute(
            """
            UPDATE Products

            SET IsActive = 0

            WHERE ProductID = ?
            """,
            (
                id,
            ),
        )


        conn.commit()

    finally:

        cursor.close()
        conn.close()


    return jsonify({
        "success": True,
    })


# =========================================================
