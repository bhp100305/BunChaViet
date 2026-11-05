from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from database import execute_query, get_connection


admin_orders_bp = Blueprint("admin_orders", __name__, url_prefix="/admin")


def check_admin() -> bool:
    return session.get("role") == "Admin"


# =========================================================
# ORDERS
# =========================================================

@admin_orders_bp.route("/orders")
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

            DeliveredAt,

            PaymentMethod,

            PaymentStatus,

            PaymentReportedAt

        FROM Orders

        WHERE 1 = 1
    """


    query_postgres = """
        SELECT "OrderID", "OrderCode", "CustomerName", "Phone", "Address", "Note",
            COALESCE("TotalMoney",0) AS "TotalMoney", "Status", "CreatedAt", "DriverID",
            COALESCE("ShippingFee",0) AS "ShippingFee",
            (COALESCE("TotalMoney",0)+COALESCE("ShippingFee",0)) AS "FinalMoney",
            "DeliveredAt", "PaymentMethod", "PaymentStatus", "PaymentReportedAt"
        FROM "Orders" WHERE 1 = 1
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


        query_postgres += ' AND CAST("CreatedAt" AS DATE) = CAST(%s AS DATE)'
        params.append(selected_date)


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


            query_postgres += ' AND EXTRACT(YEAR FROM "CreatedAt") = %s AND EXTRACT(MONTH FROM "CreatedAt") = %s'
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


        query_postgres += ' AND "Status" = %s'
        params.append(selected_status)


    query += """
        ORDER BY
            CreatedAt DESC,
            OrderID DESC
    """


    query_postgres += ' ORDER BY "CreatedAt" DESC NULLS LAST, "OrderID" DESC'

    conn = get_connection()
    cursor = conn.cursor()


    try:

        execute_query(
            cursor,
            query,
            query_postgres,
            *params,
        )


        order_rows = (
            cursor.fetchall()
        )


        # =================================================
        # SHIPPER CHO DROPDOWN
        # =================================================

        execute_query(
            cursor,
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
            """,
            """
            SELECT u."UserID", u."FullName", u."IsActive", u."IsWorking",
             (SELECT COUNT(*) FROM "Orders" ao WHERE ao."DriverID" = u."UserID" AND ao."Status" IN ('Đã giao shipper','Đang chuẩn bị','Đang giao')) AS "ActiveOrders",
             (SELECT COUNT(*) FROM "Orders" co WHERE co."DriverID" = u."UserID" AND co."Status" = 'Hoàn thành' AND CAST(COALESCE(co."DeliveredAt",co."CreatedAt") AS DATE) = CURRENT_DATE) AS "TodayCompleted",
             (SELECT MAX(dl."UpdatedAt") FROM "DriverLocations" dl WHERE dl."DriverID" = u."UserID") AS "LastLocationAt"
             FROM "Users" u WHERE u."Role" = 'Shipper' ORDER BY u."IsActive" DESC NULLS LAST, u."IsWorking" DESC NULLS LAST, u."FullName" NULLS FIRST
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

@admin_orders_bp.route(
    "/orders/<int:order_id>/confirm-payment",
    methods=["POST"],
)
def confirm_order_payment(order_id: int) -> Any:
    """Admin xác nhận khoản chuyển khoản QR từ trang đơn hàng."""

    if not check_admin():
        return jsonify({
            "success": False,
            "message": "Phiên Admin không hợp lệ hoặc đã hết hạn. Vui lòng tải lại trang và đăng nhập lại.",
        }), 403

    conn = get_connection()
    cursor = conn.cursor()

    try:
        execute_query(
            cursor,
            """
            SELECT PaymentMethod, PaymentStatus
            FROM Orders WITH (UPDLOCK, HOLDLOCK)
            WHERE OrderID = ?
            """,
            """
            SELECT "PaymentMethod", "PaymentStatus" FROM "Orders" WHERE "OrderID" = %s FOR UPDATE
            """,
            order_id,
        )
        order = cursor.fetchone()

        if not order:
            conn.rollback()
            return jsonify({"success": False, "message": "Không tìm thấy đơn hàng."}), 404

        if order.PaymentMethod != "BANK_TRANSFER":
            conn.rollback()
            return jsonify({"success": False, "message": "Đơn hàng này không thanh toán bằng QR/chuyển khoản."}), 400

        if order.PaymentStatus == "Đã thanh toán":
            conn.rollback()
            return jsonify({"success": True, "message": "Đơn hàng đã được xác nhận thanh toán."})

        if order.PaymentStatus != "Khách báo đã chuyển khoản":
            conn.rollback()
            return jsonify({"success": False, "message": "Khách chưa báo đã chuyển khoản."}), 409

        execute_query(
            cursor,
            """
            UPDATE Orders
            SET PaymentStatus = N'Đã thanh toán',
                PaidAt = SYSDATETIME()
            WHERE OrderID = ?
            """,
            """
            UPDATE "Orders" SET "PaymentStatus" = 'Đã thanh toán', "PaidAt" = CURRENT_TIMESTAMP WHERE "OrderID" = %s
            """,
            order_id,
        )
        conn.commit()
        return jsonify({"success": True, "message": "Đã xác nhận đơn hàng thanh toán qua QR."})

    except Exception as error:
        conn.rollback()
        print("LỖI XÁC NHẬN THANH TOÁN ĐƠN HÀNG:", error)
        return jsonify({"success": False, "message": "Không thể cập nhật trạng thái thanh toán."}), 500

    finally:
        cursor.close()
        conn.close()


# =========================================================
# ASSIGN ORDER
# =========================================================

@admin_orders_bp.route(
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

        execute_query(
            cursor,
            "SELECT UserID, FullName, IsActive, IsWorking FROM Users WITH (UPDLOCK, HOLDLOCK) WHERE UserID = ? AND Role = 'Shipper'",
            """
            SELECT "UserID", "FullName", "IsActive", "IsWorking" FROM "Users" WHERE "UserID" = %s AND "Role" = 'Shipper' FOR UPDATE
            """,
            driver_id,
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

        execute_query(
            cursor,
            'SELECT OrderID, OrderCode, Status, DriverID FROM Orders WITH (UPDLOCK, HOLDLOCK) WHERE OrderID = ?',
            """
            SELECT "OrderID", "OrderCode", "Status", "DriverID" FROM "Orders" WHERE "OrderID" = %s FOR UPDATE
            """,
            order_id,
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

        execute_query(
            cursor,
            """
            UPDATE Orders

            SET
                DriverID = ?,

                Status =
                    N'Đã giao shipper'

            WHERE OrderID = ?
            """,
            """
            UPDATE "Orders" SET "DriverID" = %s, "Status" = 'Đã giao shipper' WHERE "OrderID" = %s
            """,
            shipper.UserID,
            order_id,
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

@admin_orders_bp.route(
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

        execute_query(
            cursor,
            'SELECT Status, DriverID FROM Orders WITH (UPDLOCK, HOLDLOCK) WHERE OrderID = ?',
            """
            SELECT "Status", "DriverID" FROM "Orders" WHERE "OrderID" = %s FOR UPDATE
            """,
            id,
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

            execute_query(
                cursor,
                """
                UPDATE Orders

                SET
                    Status = N'Đã hủy',

                    DriverID = NULL

                WHERE OrderID = ?
                """,
                """
                UPDATE "Orders" SET "Status" = 'Đã hủy', "DriverID" = NULL WHERE "OrderID" = %s
                """,
                id,
            )

        else:

            execute_query(
                cursor,
                """
                UPDATE Orders

                SET Status = ?

                WHERE OrderID = ?
                """,
                """
                UPDATE "Orders" SET "Status" = %s WHERE "OrderID" = %s
                """,
                new_status,
                id,
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
