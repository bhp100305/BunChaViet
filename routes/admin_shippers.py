from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, render_template, request, session, redirect, url_for

from database import get_connection


admin_shippers_bp = Blueprint("admin_shippers", __name__, url_prefix="/admin")


def check_admin() -> bool:
    return session.get("role") == "Admin"


# =========================================================
# SHIPPERS
# =========================================================

@admin_shippers_bp.route("/shippers")
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

@admin_shippers_bp.route(
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

@admin_shippers_bp.route(
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

@admin_shippers_bp.route(
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
