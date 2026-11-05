from __future__ import annotations

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
from database import execute_query, get_connection

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
)

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

        execute_query(
            cursor,
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
            """,
            """
            SELECT COUNT(*) AS "TodayOrders",
                SUM(CASE WHEN "Status" = 'Hoàn thành' THEN 1 ELSE 0 END) AS "TodayCompleted",
                COALESCE(SUM(CASE WHEN "Status" = 'Hoàn thành'
                    THEN COALESCE("TotalMoney", 0) + COALESCE("ShippingFee", 0)
                    ELSE 0 END), 0) AS "TodayCollected"
            FROM "Orders"
            WHERE CAST("CreatedAt" AS DATE) = CURRENT_DATE
            """,
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

        execute_query(
            cursor,
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
            """,
            """
            SELECT SUM(CASE WHEN "Status" = 'Đã tiếp nhận' THEN 1 ELSE 0 END) AS "PendingOrders",
                SUM(CASE WHEN "Status" IN ('Đã giao shipper', 'Đang chuẩn bị', 'Đang giao')
                    THEN 1 ELSE 0 END) AS "ActiveOrders",
                SUM(CASE WHEN "Status" IN ('Không giao được', 'Đã hủy')
                    THEN 1 ELSE 0 END) AS "FailedOrders"
            FROM "Orders"
            """,
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

        execute_query(
            cursor,
            """
            SELECT COUNT(*)

            FROM Products

            WHERE IsActive = 1
            """,
            'SELECT COUNT(*) AS "ActiveProducts" FROM "Products" WHERE "IsActive" = TRUE',
        )

        active_products = (
            cursor.fetchone()[0]
            or 0
        )


        # =================================================
        # SHIPPER
        # =================================================

        execute_query(
            cursor,
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
            """,
            """
            SELECT COUNT(*) AS "TotalShippers",
                SUM(CASE WHEN "IsActive" = TRUE AND "IsWorking" = TRUE
                    THEN 1 ELSE 0 END) AS "OnlineShippers"
            FROM "Users" WHERE "Role" = 'Shipper'
            """,
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

        execute_query(
            cursor,
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
            """,
            """
            SELECT o."OrderID", o."OrderCode", o."CustomerName",
                (COALESCE(o."TotalMoney", 0) + COALESCE(o."ShippingFee", 0)) AS "FinalMoney",
                o."Status",
                CASE WHEN o."CreatedAt" IS NULL THEN ''
                    ELSE TO_CHAR(o."CreatedAt", 'DD/MM/YYYY HH24:MI') END AS "CreatedTime",
                COALESCE(u."FullName", 'Chưa giao shipper') AS "ShipperName"
            FROM "Orders" o LEFT JOIN "Users" u ON o."DriverID" = u."UserID"
            ORDER BY o."CreatedAt" DESC NULLS LAST, o."OrderID" DESC
            LIMIT 6
            """,
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
