from __future__ import annotations

import os
from typing import Any

from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

from database import get_connection


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
)

UPLOAD_FOLDER = "static/images"


# =========================================================
# CHECK ADMIN
# =========================================================

def check_admin() -> bool:
    """Kiểm tra session hiện tại có phải Admin không."""

    return session.get("role") == "Admin"


# =========================================================
# DASHBOARD
# =========================================================

@admin_bp.route("/dashboard")
def dashboard() -> Any:
    """Dashboard Admin với dữ liệu thật từ database."""

    if not check_admin():
        return redirect(
            url_for("login")
        )

    conn = get_connection()
    cursor = conn.cursor()

    try:

        # =================================================
        # THỐNG KÊ ĐƠN HÔM NAY
        # =================================================

        cursor.execute(
            """
            SELECT
                COUNT(*) AS TodayOrders,

                SUM(
                    CASE
                        WHEN Status = N'Hoàn thành'
                        THEN 1
                        ELSE 0
                    END
                ) AS TodayCompleted,

                ISNULL(
                    SUM(
                        CASE
                            WHEN Status = N'Hoàn thành'
                            THEN
                                ISNULL(TotalMoney, 0)
                                +
                                ISNULL(ShippingFee, 0)

                            ELSE 0
                        END
                    ),
                    0
                ) AS TodayCollected

            FROM Orders

            WHERE
                CAST(CreatedAt AS DATE)
                =
                CAST(GETDATE() AS DATE)
            """
        )

        today_row = cursor.fetchone()

        today_orders = (
            today_row[0]
            or 0
        )

        today_completed = (
            today_row[1]
            or 0
        )

        today_collected = (
            today_row[2]
            or 0
        )


        # =================================================
        # TRẠNG THÁI ĐƠN TOÀN HỆ THỐNG
        # =================================================

        cursor.execute(
            """
            SELECT

                SUM(
                    CASE
                        WHEN Status = N'Đã tiếp nhận'
                        THEN 1
                        ELSE 0
                    END
                ) AS PendingOrders,


                SUM(
                    CASE

                        WHEN Status IN
                        (
                            N'Đã giao shipper',
                            N'Đang chuẩn bị',
                            N'Đang giao'
                        )

                        THEN 1
                        ELSE 0

                    END
                ) AS ActiveOrders,


                SUM(
                    CASE

                        WHEN Status IN
                        (
                            N'Không giao được',
                            N'Đã hủy'
                        )

                        THEN 1
                        ELSE 0

                    END
                ) AS FailedOrders

            FROM Orders
            """
        )

        order_status_row = (
            cursor.fetchone()
        )

        pending_orders = (
            order_status_row[0]
            or 0
        )

        active_orders = (
            order_status_row[1]
            or 0
        )

        failed_orders = (
            order_status_row[2]
            or 0
        )


        # =================================================
        # SẢN PHẨM ĐANG BÁN
        # =================================================

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM Products

            WHERE IsActive = 1
            """
        )

        active_products = (
            cursor.fetchone()[0]
            or 0
        )


        # =================================================
        # SHIPPER
        # =================================================

        cursor.execute(
            """
            SELECT

                COUNT(*) AS TotalShippers,

                SUM(
                    CASE

                        WHEN
                            IsActive = 1
                            AND
                            IsWorking = 1

                        THEN 1

                        ELSE 0

                    END
                ) AS OnlineShippers

            FROM Users

            WHERE Role = 'Shipper'
            """
        )

        shipper_row = (
            cursor.fetchone()
        )

        total_shippers = (
            shipper_row[0]
            or 0
        )

        online_shippers = (
            shipper_row[1]
            or 0
        )


        # =================================================
        # 6 ĐƠN GẦN NHẤT
        # =================================================

        cursor.execute(
            """
            SELECT TOP 6

                o.OrderID,

                o.OrderCode,

                o.CustomerName,

                (
                    ISNULL(
                        o.TotalMoney,
                        0
                    )
                    +
                    ISNULL(
                        o.ShippingFee,
                        0
                    )
                ) AS FinalMoney,

                o.Status,


                CASE

                    WHEN o.CreatedAt IS NULL

                    THEN ''

                    ELSE

                        CONVERT(
                            VARCHAR(10),
                            o.CreatedAt,
                            103
                        )

                        + ' '

                        +

                        LEFT(
                            CONVERT(
                                VARCHAR(8),
                                o.CreatedAt,
                                108
                            ),
                            5
                        )

                END AS CreatedTime,


                ISNULL(
                    u.FullName,
                    N'Chưa giao shipper'
                ) AS ShipperName


            FROM Orders o


            LEFT JOIN Users u
                ON o.DriverID = u.UserID


            ORDER BY
                o.CreatedAt DESC,
                o.OrderID DESC
            """
        )

        recent_orders = (
            cursor.fetchall()
        )

    finally:

        cursor.close()
        conn.close()


    return render_template(
        "admin/dashboard.html",

        username=(
            session.get("fullname")
            or "Admin"
        ),

        today_orders=(
            today_orders
        ),

        today_completed=(
            today_completed
        ),

        today_collected=(
            today_collected
        ),

        pending_orders=(
            pending_orders
        ),

        active_orders=(
            active_orders
        ),

        failed_orders=(
            failed_orders
        ),

        active_products=(
            active_products
        ),

        total_shippers=(
            total_shippers
        ),

        online_shippers=(
            online_shippers
        ),

        recent_orders=(
            recent_orders
        ),
    )


# =========================================================
# PRODUCTS
# =========================================================

@admin_bp.route("/products")
def products() -> Any:
    """Hiển thị danh sách sản phẩm."""

    if not check_admin():
        return redirect(
            url_for("login")
        )

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
                c.CategoryName

            FROM Products p

            LEFT JOIN Categories c
                ON p.CategoryID = c.CategoryID

            WHERE p.IsActive = 1

            ORDER BY p.ProductID DESC
            """
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
    )


# =========================================================
# ADD PRODUCT
# =========================================================

@admin_bp.route(
    "/products/add",
    methods=["POST"],
)
def add_product() -> Any:
    """Thêm sản phẩm."""

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


    filename = ""


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


    conn = get_connection()
    cursor = conn.cursor()


    try:

        cursor.execute(
            """
            INSERT INTO Products
            (
                ProductName,
                Description,
                Price,
                Image,
                CategoryID,
                IsActive
            )

            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                ?,
                1
            )
            """,
            (
                name,
                description,
                price,
                filename,
                category,
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
# UPDATE PRODUCT
# =========================================================

@admin_bp.route(
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
# DELETE PRODUCT
# =========================================================

@admin_bp.route(
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
# USERS
# =========================================================

@admin_bp.route("/users")
def users() -> Any:

    if not check_admin():

        return redirect(
            url_for("login")
        )


    return render_template(
        "admin/users.html"
    )


# =========================================================
# CATEGORIES
# =========================================================

@admin_bp.route("/categories")
def categories() -> Any:

    if not check_admin():

        return redirect(
            url_for("login")
        )


    return render_template(
        "admin/categories.html"
    )


# =========================================================
# ORDERS
# =========================================================

@admin_bp.route("/orders")
def orders() -> Any:
    """Trang quản lý đơn hàng."""

    if not check_admin():

        return redirect(
            url_for("login")
        )


    selected_date = (
        request.args.get("date")
        or ""
    ).strip()


    selected_month = (
        request.args.get("month")
        or ""
    ).strip()


    selected_status = (
        request.args.get("status")
        or ""
    ).strip()


    query = """
        SELECT
            OrderID,
            OrderCode,
            CustomerName,
            Phone,
            Address,
            Note,

            ISNULL(
                TotalMoney,
                0
            ) AS TotalMoney,

            Status,

            CreatedAt,

            DriverID,

            ISNULL(
                ShippingFee,
                0
            ) AS ShippingFee,

            (
                ISNULL(
                    TotalMoney,
                    0
                )
                +
                ISNULL(
                    ShippingFee,
                    0
                )
            ) AS FinalMoney,

            DeliveredAt

        FROM Orders

        WHERE 1 = 1
    """


    params: list[Any] = []


    if selected_date:

        query += """
            AND CAST(
                CreatedAt
            AS DATE)

            =
            CONVERT(
                DATE,
                ?,
                23
            )
        """


        params.append(
            selected_date
        )


    elif selected_month:

        try:

            year_text, month_text = (
                selected_month.split(
                    "-",
                    1,
                )
            )


            year = int(
                year_text
            )


            month_number = int(
                month_text
            )


            if (
                month_number < 1
                or
                month_number > 12
            ):

                raise ValueError(
                    "Invalid month"
                )


            query += """
                AND YEAR(CreatedAt) = ?

                AND MONTH(CreatedAt) = ?
            """


            params.extend([
                year,
                month_number,
            ])


        except (
            ValueError,
            TypeError,
        ):

            selected_month = ""


    if selected_status:

        query += """
            AND Status = ?
        """


        params.append(
            selected_status
        )


    query += """
        ORDER BY
            CreatedAt DESC,
            OrderID DESC
    """


    conn = get_connection()
    cursor = conn.cursor()


    try:

        cursor.execute(
            query,
            params,
        )


        order_rows = (
            cursor.fetchall()
        )


        # =================================================
        # SHIPPER CHO DROPDOWN
        # =================================================

        cursor.execute(
            """
            SELECT
                u.UserID,

                u.FullName,

                u.IsActive,

                u.IsWorking,


                (
                    SELECT COUNT(*)

                    FROM Orders ao

                    WHERE
                        ao.DriverID = u.UserID

                    AND ao.Status IN
                    (
                        N'Đã giao shipper',
                        N'Đang chuẩn bị',
                        N'Đang giao'
                    )

                ) AS ActiveOrders,


                (
                    SELECT COUNT(*)

                    FROM Orders co

                    WHERE
                        co.DriverID = u.UserID

                    AND co.Status =
                        N'Hoàn thành'

                    AND CAST(
                        ISNULL(
                            co.DeliveredAt,
                            co.CreatedAt
                        )
                    AS DATE)

                    =
                    CAST(
                        GETDATE()
                    AS DATE)

                ) AS TodayCompleted,


                (
                    SELECT
                        MAX(
                            dl.UpdatedAt
                        )

                    FROM DriverLocations dl

                    WHERE
                        dl.DriverID =
                        u.UserID

                ) AS LastLocationAt


            FROM Users u


            WHERE
                u.Role = 'Shipper'


            ORDER BY
                u.IsActive DESC,
                u.IsWorking DESC,
                u.FullName
            """
        )


        shipper_rows = (
            cursor.fetchall()
        )

    finally:

        cursor.close()
        conn.close()


    grouped_orders: dict[
        Any,
        list[Any],
    ] = {}


    for order in order_rows:

        created_at = (
            order.CreatedAt
        )


        order_date = (
            created_at.date()
            if created_at
            else None
        )


        grouped_orders.setdefault(
            order_date,
            [],
        ).append(
            order
        )


    return render_template(
        "admin/orders.html",

        orders=order_rows,

        grouped_orders=(
            grouped_orders
        ),

        shippers=shipper_rows,

        selected_date=(
            selected_date
        ),

        selected_month=(
            selected_month
        ),

        selected_status=(
            selected_status
        ),
    )


# =========================================================
# ASSIGN ORDER
# =========================================================

@admin_bp.route(
    "/orders/assign",
    methods=["POST"],
)
def assign_shipper() -> Any:
    """Giao đơn cho shipper đang hoạt động."""

    if not check_admin():

        return jsonify({
            "success": False,
            "message": "Không có quyền.",
        }), 403


    data = (
        request.get_json(
            silent=True
        )
        or {}
    )


    order_id = data.get(
        "orderId"
    )


    driver_id = data.get(
        "driverId"
    )


    if (
        not order_id
        or
        not driver_id
    ):

        return jsonify({
            "success": False,

            "message":
                "Thiếu thông tin đơn hàng hoặc shipper.",
        }), 400


    conn = get_connection()
    cursor = conn.cursor()


    try:

        # =================================================
        # CHECK SHIPPER
        # =================================================

        cursor.execute(
            """
            SELECT
                UserID,
                FullName,
                IsActive,
                IsWorking

            FROM Users

            WHERE UserID = ?

              AND Role = 'Shipper'
            """,
            (
                driver_id,
            ),
        )


        shipper = (
            cursor.fetchone()
        )


        if not shipper:

            return jsonify({
                "success": False,
                "message":
                    "Không tìm thấy shipper.",
            }), 404


        if shipper.IsActive != 1:

            return jsonify({
                "success": False,

                "message":
                    f"{shipper.FullName} "
                    "đang bị khóa tài khoản.",
            }), 400


        if shipper.IsWorking != 1:

            return jsonify({
                "success": False,

                "message":
                    f"{shipper.FullName} "
                    "đang nghỉ ca, không thể giao đơn.",
            }), 400


        # =================================================
        # CHECK ORDER
        # =================================================

        cursor.execute(
            """
            SELECT
                OrderID,
                OrderCode,
                Status,
                DriverID

            FROM Orders

            WHERE OrderID = ?
            """,
            (
                order_id,
            ),
        )


        order = (
            cursor.fetchone()
        )


        if not order:

            return jsonify({
                "success": False,

                "message":
                    "Không tìm thấy đơn hàng.",
            }), 404


        # =================================================
        # FINISHED ORDER
        # =================================================

        if order.Status in (
            "Hoàn thành",
            "Đã hủy",
            "Không giao được",
        ):

            return jsonify({
                "success": False,

                "message":
                    "Đơn hàng đã kết thúc, "
                    "không thể giao lại cho shipper.",
            }), 400


        # =================================================
        # DELIVERY IN PROGRESS
        # =================================================

        if (
            order.Status == "Đang giao"
            and
            order.DriverID
            != shipper.UserID
        ):

            return jsonify({
                "success": False,

                "message":
                    "Đơn đang được một shipper khác giao, "
                    "không thể đổi shipper lúc này.",
            }), 400


        # =================================================
        # ALREADY ASSIGNED
        # =================================================

        if (
            order.DriverID
            == shipper.UserID

            and

            order.Status in (
                "Đã giao shipper",
                "Đang chuẩn bị",
                "Đang giao",
            )
        ):

            return jsonify({
                "success": True,

                "message":
                    f"Đơn đã được giao cho "
                    f"{shipper.FullName}.",
            })


        # =================================================
        # ASSIGN
        # =================================================

        cursor.execute(
            """
            UPDATE Orders

            SET
                DriverID = ?,

                Status =
                    N'Đã giao shipper'

            WHERE OrderID = ?
            """,
            (
                shipper.UserID,
                order_id,
            ),
        )


        conn.commit()


        return jsonify({
            "success": True,

            "message":
                f"Đã giao đơn cho "
                f"{shipper.FullName}.",
        })

    finally:

        cursor.close()
        conn.close()


# =========================================================
# ADMIN UPDATE ORDER STATUS
# =========================================================

@admin_bp.route(
    "/orders/update/<int:id>",
    methods=["POST"],
)
def update_order_status(
    id: int,
) -> Any:
    """Admin cập nhật các trạng thái thuộc luồng Admin."""

    if not check_admin():

        return jsonify({
            "success": False,
            "message": "Không có quyền.",
        }), 403


    data = (
        request.get_json(
            silent=True
        )
        or {}
    )


    new_status = (
        data.get("status")
        or ""
    ).strip()


    allowed_statuses = {
        "Đã tiếp nhận",
        "Đang chuẩn bị",
        "Đã hủy",
    }


    if (
        new_status
        not in allowed_statuses
    ):

        return jsonify({
            "success": False,

            "message":
                "Admin chỉ được cập nhật "
                "Đã tiếp nhận, Đang chuẩn bị hoặc Đã hủy.",
        }), 400


    conn = get_connection()
    cursor = conn.cursor()


    try:

        cursor.execute(
            """
            SELECT
                Status,
                DriverID

            FROM Orders

            WHERE OrderID = ?
            """,
            (
                id,
            ),
        )


        order = (
            cursor.fetchone()
        )


        if not order:

            return jsonify({
                "success": False,

                "message":
                    "Không tìm thấy đơn hàng.",
            }), 404


        if order.Status in (
            "Hoàn thành",
            "Không giao được",
        ):

            return jsonify({
                "success": False,

                "message":
                    "Đơn đã kết thúc, "
                    "không thể sửa trạng thái.",
            }), 400


        if (
            new_status == "Đã hủy"
            and
            order.Status == "Đang giao"
        ):

            return jsonify({
                "success": False,

                "message":
                    "Đơn đang giao. "
                    "Hãy liên hệ shipper trước khi hủy.",
            }), 400


        if new_status == "Đã hủy":

            cursor.execute(
                """
                UPDATE Orders

                SET
                    Status = N'Đã hủy',

                    DriverID = NULL

                WHERE OrderID = ?
                """,
                (
                    id,
                ),
            )

        else:

            cursor.execute(
                """
                UPDATE Orders

                SET Status = ?

                WHERE OrderID = ?
                """,
                (
                    new_status,
                    id,
                ),
            )


        conn.commit()


        return jsonify({
            "success": True,

            "message":
                "Cập nhật trạng thái thành công.",
        })

    finally:

        cursor.close()
        conn.close()


# =========================================================
# SHIPPERS
# =========================================================

@admin_bp.route("/shippers")
def shippers() -> Any:
    """Trang quản lý shipper."""

    if not check_admin():

        return redirect(
            url_for("login")
        )


    conn = get_connection()
    cursor = conn.cursor()


    try:

        cursor.execute(
            """
            SELECT
                u.UserID,

                u.Username,

                u.FullName,

                u.Phone,

                u.IsActive,

                u.IsWorking,


                (
                    SELECT COUNT(*)

                    FROM Orders ao

                    WHERE
                        ao.DriverID = u.UserID

                    AND ao.Status IN
                    (
                        N'Đã giao shipper',
                        N'Đang chuẩn bị',
                        N'Đang giao'
                    )

                ) AS ActiveOrders,


                (
                    SELECT COUNT(*)

                    FROM Orders co

                    WHERE
                        co.DriverID = u.UserID

                    AND co.Status =
                        N'Hoàn thành'

                    AND CAST(
                        ISNULL(
                            co.DeliveredAt,
                            co.CreatedAt
                        )
                    AS DATE)

                    =
                    CAST(
                        GETDATE()
                    AS DATE)

                ) AS TodayCompleted,


                (
                    SELECT COUNT(*)

                    FROM Orders fo

                    WHERE
                        fo.DriverID = u.UserID

                    AND fo.Status =
                        N'Không giao được'

                ) AS FailedOrders,


                (
                    SELECT
                        MAX(
                            dl.UpdatedAt
                        )

                    FROM DriverLocations dl

                    WHERE
                        dl.DriverID =
                        u.UserID

                ) AS LastLocationAt


            FROM Users u


            WHERE
                u.Role = 'Shipper'


            ORDER BY
                u.IsActive DESC,
                u.IsWorking DESC,
                u.UserID DESC
            """
        )


        shipper_rows = (
            cursor.fetchall()
        )

    finally:

        cursor.close()
        conn.close()


    return render_template(
        "admin/shippers.html",

        shippers=shipper_rows,
    )


# =========================================================
# ADD SHIPPER
# =========================================================

@admin_bp.route(
    "/shippers/add",
    methods=["POST"],
)
def add_shipper() -> Any:
    """Thêm tài khoản shipper."""

    if not check_admin():

        return jsonify({
            "success": False,
            "message": "Không có quyền.",
        }), 403


    data = (
        request.get_json(
            silent=True
        )
        or {}
    )


    fullname = (
        data.get("fullname")
        or ""
    ).strip()


    username = (
        data.get("username")
        or ""
    ).strip()


    password = (
        data.get("password")
        or ""
    )


    phone = (
        data.get("phone")
        or ""
    ).strip()


    if (
        not fullname
        or
        not username
        or
        not password
    ):

        return jsonify({
            "success": False,

            "message":
                "Vui lòng nhập họ tên, tài khoản và mật khẩu.",
        }), 400


    conn = get_connection()
    cursor = conn.cursor()


    try:

        cursor.execute(
            """
            SELECT UserID

            FROM Users

            WHERE Username = ?
            """,
            (
                username,
            ),
        )


        if cursor.fetchone():

            return jsonify({
                "success": False,

                "message":
                    "Tên đăng nhập đã tồn tại.",
            }), 400


        cursor.execute(
            """
            INSERT INTO Users
            (
                Username,
                Password,
                FullName,
                Phone,
                Role,
                IsActive,
                IsWorking
            )

            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                'Shipper',
                1,
                0
            )
            """,
            (
                username,
                password,
                fullname,
                phone,
            ),
        )


        conn.commit()


        return jsonify({
            "success": True,

            "message":
                "Thêm shipper thành công.",
        })

    finally:

        cursor.close()
        conn.close()


# =========================================================
# UPDATE SHIPPER
# =========================================================

@admin_bp.route(
    "/shippers/update/<int:id>",
    methods=["POST"],
)
def update_shipper(
    id: int,
) -> Any:
    """Cập nhật shipper."""

    if not check_admin():

        return jsonify({
            "success": False,
            "message": "Không có quyền.",
        }), 403


    data = (
        request.get_json(
            silent=True
        )
        or {}
    )


    fullname = (
        data.get("fullname")
        or ""
    ).strip()


    username = (
        data.get("username")
        or ""
    ).strip()


    password = (
        data.get("password")
        or ""
    )


    phone = (
        data.get("phone")
        or ""
    ).strip()


    if (
        not fullname
        or
        not username
    ):

        return jsonify({
            "success": False,

            "message":
                "Họ tên và tên đăng nhập "
                "không được để trống.",
        }), 400


    conn = get_connection()
    cursor = conn.cursor()


    try:

        cursor.execute(
            """
            SELECT UserID

            FROM Users

            WHERE Username = ?

              AND UserID <> ?
            """,
            (
                username,
                id,
            ),
        )


        if cursor.fetchone():

            return jsonify({
                "success": False,

                "message":
                    "Tên đăng nhập đã được sử dụng.",
            }), 400


        cursor.execute(
            """
            SELECT UserID

            FROM Users

            WHERE UserID = ?

              AND Role = 'Shipper'
            """,
            (
                id,
            ),
        )


        if not cursor.fetchone():

            return jsonify({
                "success": False,

                "message":
                    "Không tìm thấy shipper.",
            }), 404


        if password:

            cursor.execute(
                """
                UPDATE Users

                SET
                    Username = ?,
                    Password = ?,
                    FullName = ?,
                    Phone = ?

                WHERE UserID = ?

                  AND Role = 'Shipper'
                """,
                (
                    username,
                    password,
                    fullname,
                    phone,
                    id,
                ),
            )

        else:

            cursor.execute(
                """
                UPDATE Users

                SET
                    Username = ?,
                    FullName = ?,
                    Phone = ?

                WHERE UserID = ?

                  AND Role = 'Shipper'
                """,
                (
                    username,
                    fullname,
                    phone,
                    id,
                ),
            )


        conn.commit()


        return jsonify({
            "success": True,

            "message":
                "Cập nhật shipper thành công.",
        })

    finally:

        cursor.close()
        conn.close()


# =========================================================
# LOCK / UNLOCK SHIPPER
# =========================================================

@admin_bp.route(
    "/shippers/status/<int:id>",
    methods=["POST"],
)
def update_shipper_status(
    id: int,
) -> Any:
    """Khóa hoặc mở khóa tài khoản shipper."""

    if not check_admin():

        return jsonify({
            "success": False,
            "message": "Không có quyền.",
        }), 403


    data = (
        request.get_json(
            silent=True
        )
        or {}
    )


    is_active = data.get(
        "isActive"
    )


    if is_active not in (
        0,
        1,
        False,
        True,
    ):

        return jsonify({
            "success": False,

            "message":
                "Trạng thái tài khoản không hợp lệ.",
        }), 400


    normalized_status = (
        1
        if bool(is_active)
        else 0
    )


    conn = get_connection()
    cursor = conn.cursor()


    try:

        cursor.execute(
            """
            SELECT
                UserID,
                FullName,
                IsActive

            FROM Users

            WHERE UserID = ?

              AND Role = 'Shipper'
            """,
            (
                id,
            ),
        )


        shipper = (
            cursor.fetchone()
        )


        if not shipper:

            return jsonify({
                "success": False,

                "message":
                    "Không tìm thấy shipper.",
            }), 404


        # =================================================
        # LOCK
        # =================================================

        if normalized_status == 0:

            cursor.execute(
                """
                SELECT COUNT(*)

                FROM Orders

                WHERE DriverID = ?

                  AND Status IN
                  (
                      N'Đã giao shipper',
                      N'Đang chuẩn bị',
                      N'Đang giao'
                  )
                """,
                (
                    id,
                ),
            )


            active_orders = (
                cursor.fetchone()[0]
                or 0
            )


            if active_orders > 0:

                return jsonify({
                    "success": False,

                    "message":
                        f"{shipper.FullName} còn "
                        f"{active_orders} đơn đang xử lý. "
                        "Không thể khóa tài khoản lúc này.",
                }), 400


            cursor.execute(
                """
                UPDATE Users

                SET
                    IsActive = 0,
                    IsWorking = 0

                WHERE UserID = ?

                  AND Role = 'Shipper'
                """,
                (
                    id,
                ),
            )


        # =================================================
        # UNLOCK
        # =================================================

        else:

            cursor.execute(
                """
                UPDATE Users

                SET
                    IsActive = 1,
                    IsWorking = 0

                WHERE UserID = ?

                  AND Role = 'Shipper'
                """,
                (
                    id,
                ),
            )


        conn.commit()


        return jsonify({
            "success": True,

            "message":
                "Cập nhật trạng thái shipper thành công.",
        })

    finally:

        cursor.close()
        conn.close()