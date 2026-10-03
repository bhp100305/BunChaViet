from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    jsonify,
    request
)

from database import get_connection


shipper_bp = Blueprint(
    "shipper",
    __name__,
    url_prefix="/shipper"
)


# =====================================================
# CHECK ROLE
# =====================================================

def check_shipper():
    return session.get("role") == "Shipper"


# =====================================================
# SHIPPER DASHBOARD
# =====================================================

@shipper_bp.route("/orders")
def orders():

    if not check_shipper():
        return redirect(
            url_for("login")
        )

    user_id = session.get("user_id")


    # =================================================
    # NGÀY THỐNG KÊ
    # QUAN TRỌNG:
    # luôn giữ dưới dạng STRING YYYY-MM-DD
    # không truyền object date vào pyodbc
    # =================================================

    selected_date = request.args.get("date")

    if selected_date:

        try:

            datetime.strptime(
                selected_date,
                "%Y-%m-%d"
            )

        except ValueError:

            selected_date = (
                datetime.now()
                .strftime("%Y-%m-%d")
            )

    else:

        selected_date = (
            datetime.now()
            .strftime("%Y-%m-%d")
        )


    conn = get_connection()

    cursor = conn.cursor()


    try:

        # =================================================
        # LẤY TRẠNG THÁI LÀM VIỆC
        # =================================================

        cursor.execute(
            """
            SELECT IsWorking

            FROM Users

            WHERE UserID = ?
            """,
            (
                user_id,
            )
        )


        working = cursor.fetchone()


        is_working = 0


        if working:

            is_working = working[0]


        # =================================================
        # THỐNG KÊ TỔNG QUAN
        # =================================================

        cursor.execute(
            """
            SELECT

                COUNT(*),

                SUM(
                    CASE

                        WHEN CAST(
                            ISNULL(
                                DeliveredAt,
                                CreatedAt
                            )
                        AS DATE)

                        =
                        CAST(GETDATE() AS DATE)

                        THEN 1

                        ELSE 0

                    END
                ),

                SUM(
                    CASE

                        WHEN MONTH(
                            ISNULL(
                                DeliveredAt,
                                CreatedAt
                            )
                        )
                        =
                        MONTH(GETDATE())

                        AND

                        YEAR(
                            ISNULL(
                                DeliveredAt,
                                CreatedAt
                            )
                        )
                        =
                        YEAR(GETDATE())

                        THEN 1

                        ELSE 0

                    END
                )

            FROM Orders

            WHERE DriverID = ?

            AND Status = N'Hoàn thành'
            """,
            (
                user_id,
            )
        )


        statistic = cursor.fetchone()


        total_done = statistic[0] or 0

        today_done = statistic[1] or 0

        month_done = statistic[2] or 0


        # =================================================
        # LẤY TOÀN BỘ ĐƠN CỦA SHIPPER
        # =================================================

        cursor.execute(
            """
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

                Status,

                CreatedAt

            FROM Orders

            WHERE DriverID = ?

            ORDER BY OrderID DESC
            """,
            (
                user_id,
            )
        )


        orders = cursor.fetchall()


        # =================================================
        # THỐNG KÊ THEO NGÀY
        #
        # selected_date là STRING
        # ví dụ "2026-09-30"
        #
        # SQL Server tự convert STRING -> DATE
        # =================================================

        cursor.execute(
            """
            SELECT

                COUNT(*) AS DailyCount,

                ISNULL(
                    SUM(
                        ISNULL(
                            TotalMoney,
                            0
                        )
                        +
                        ISNULL(
                            ShippingFee,
                            0
                        )
                    ),
                    0
                ) AS DailyTotal

            FROM Orders

            WHERE DriverID = ?

            AND Status = N'Hoàn thành'

            AND CAST(
                ISNULL(
                    DeliveredAt,
                    CreatedAt
                )
            AS DATE)

            =
            CONVERT(
                DATE,
                ?,
                23
            )
            """,
            (
                user_id,
                selected_date
            )
        )


        daily_stat = cursor.fetchone()


        daily_count = daily_stat[0] or 0

        daily_total = daily_stat[1] or 0


        # =================================================
        # DANH SÁCH ĐƠN ĐÃ GIAO TRONG NGÀY
        # =================================================

        cursor.execute(
            """
            SELECT

                OrderID,

                OrderCode,

                CustomerName,

                Phone,

                Address,

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

                ISNULL(
                    DeliveredAt,
                    CreatedAt
                ) AS DeliveredTime

            FROM Orders

            WHERE DriverID = ?

            AND Status = N'Hoàn thành'

            AND CAST(
                ISNULL(
                    DeliveredAt,
                    CreatedAt
                )
            AS DATE)

            =
            CONVERT(
                DATE,
                ?,
                23
            )

            ORDER BY
                ISNULL(
                    DeliveredAt,
                    CreatedAt
                )
            DESC
            """,
            (
                user_id,
                selected_date
            )
        )


        daily_orders = cursor.fetchall()


    finally:

        cursor.close()

        conn.close()


    return render_template(

        "shipper/orders.html",

        orders=orders,

        username=session.get("fullname"),

        is_working=is_working,

        total_done=total_done,

        today_done=today_done,

        month_done=month_done,

        selected_date=selected_date,

        daily_count=daily_count,

        daily_total=daily_total,

        daily_orders=daily_orders

    )


# =====================================================
# BẬT / TẮT NHẬN ĐƠN
# =====================================================

@shipper_bp.route(
    "/toggle-work",
    methods=["POST"]
)
def toggle_work():

    if not check_shipper():

        return jsonify({
            "success": False,
            "message": "Không có quyền"
        }), 403


    user_id = session.get("user_id")


    conn = get_connection()

    cursor = conn.cursor()


    try:

        cursor.execute(
            """
            SELECT IsWorking

            FROM Users

            WHERE UserID = ?
            """,
            (
                user_id,
            )
        )


        current = cursor.fetchone()


        if not current:

            return jsonify({
                "success": False,
                "message": "Không tìm thấy shipper"
            }), 404


        current_status = current[0]


        # =============================================
        # Nếu đang làm -> muốn nghỉ ca
        #
        # Không cho nghỉ nếu vẫn còn đơn
        # =============================================

        if current_status == 1:

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
                    user_id,
                )
            )


            active_orders = cursor.fetchone()[0]


            if active_orders > 0:

                return jsonify({
                    "success": False,
                    "message":
                        "Bạn còn đơn chưa hoàn thành. "
                        "Hãy hoàn thành hoặc xử lý đơn trước khi nghỉ ca."
                }), 400


        new_status = (
            0
            if current_status == 1
            else 1
        )


        cursor.execute(
            """
            UPDATE Users

            SET IsWorking = ?

            WHERE UserID = ?
            """,
            (
                new_status,
                user_id
            )
        )


        conn.commit()


        return jsonify({
            "success": True,
            "working": new_status
        })


    finally:

        cursor.close()

        conn.close()


# =====================================================
# UPDATE ORDER STATUS
# =====================================================

@shipper_bp.route(
    "/update/<int:id>",
    methods=["POST"]
)
def update_status(id):

    if not check_shipper():

        return jsonify({
            "success": False,
            "message": "Không có quyền"
        }), 403


    data = request.get_json() or {}


    status = data.get("status")


    allowed_status = [

        "Đang chuẩn bị",

        "Đang giao",

        "Hoàn thành"

    ]


    if status not in allowed_status:

        return jsonify({
            "success": False,
            "message": "Trạng thái không hợp lệ"
        }), 400


    user_id = session.get("user_id")


    conn = get_connection()

    cursor = conn.cursor()


    try:

        # =============================================
        # KIỂM TRA ĐƠN CÓ THUỘC SHIPPER KHÔNG
        # =============================================

        cursor.execute(
            """
            SELECT
                OrderID,
                Status

            FROM Orders

            WHERE OrderID = ?

            AND DriverID = ?
            """,
            (
                id,
                user_id
            )
        )


        order = cursor.fetchone()


        if not order:

            return jsonify({
                "success": False,
                "message":
                    "Không tìm thấy đơn hàng "
                    "hoặc đơn không thuộc về bạn"
            }), 404


        old_status = order[1]


        if old_status in (
            "Hoàn thành",
            "Không giao được",
            "Đã hủy"
        ):

            return jsonify({
                "success": False,
                "message": "Đơn hàng này đã kết thúc"
            }), 400


        # =============================================
        # HOÀN THÀNH
        # =============================================

        if status == "Hoàn thành":

            cursor.execute(
                """
                UPDATE Orders

                SET
                    Status = N'Hoàn thành',

                    DeliveredAt = GETDATE()

                WHERE OrderID = ?

                AND DriverID = ?
                """,
                (
                    id,
                    user_id
                )
            )


        else:

            cursor.execute(
                """
                UPDATE Orders

                SET Status = ?

                WHERE OrderID = ?

                AND DriverID = ?
                """,
                (
                    status,
                    id,
                    user_id
                )
            )


        conn.commit()


        return jsonify({
            "success": True,
            "message": "Cập nhật thành công"
        })


    finally:

        cursor.close()

        conn.close()


# =====================================================
# KHÔNG GIAO ĐƯỢC
# =====================================================

@shipper_bp.route(
    "/cancel/<int:id>",
    methods=["POST"]
)
def cancel_order(id):

    if not check_shipper():

        return jsonify({
            "success": False,
            "message": "Không có quyền"
        }), 403


    data = request.get_json() or {}


    reason = (
        data.get("reason")
        or ""
    ).strip()


    note = (
        data.get("note")
        or ""
    ).strip()


    if not reason:

        return jsonify({
            "success": False,
            "message":
                "Bạn cần chọn lý do không giao được"
        }), 400


    user_id = session.get("user_id")


    conn = get_connection()

    cursor = conn.cursor()


    try:

        cursor.execute(
            """
            SELECT
                Status,
                Note

            FROM Orders

            WHERE OrderID = ?

            AND DriverID = ?
            """,
            (
                id,
                user_id
            )
        )


        order = cursor.fetchone()


        if not order:

            return jsonify({
                "success": False,
                "message": "Không tìm thấy đơn hàng"
            }), 404


        current_status = order[0]

        old_note = order[1] or ""


        if current_status != "Đang giao":

            return jsonify({
                "success": False,
                "message":
                    "Chỉ đơn đang giao mới có thể "
                    "báo không giao được"
            }), 400


        cancel_text = (
            "Không giao được - "
            + reason
        )


        if note:

            cancel_text += (
                " - Ghi chú: "
                + note
            )


        if old_note:

            new_note = (
                old_note
                + " | "
                + cancel_text
            )

        else:

            new_note = cancel_text


        cursor.execute(
            """
            UPDATE Orders

            SET
                Status = N'Không giao được',

                Note = ?

            WHERE OrderID = ?

            AND DriverID = ?
            """,
            (
                new_note,
                id,
                user_id
            )
        )


        conn.commit()


        return jsonify({
            "success": True,
            "message":
                "Đã ghi nhận đơn không giao được"
        })


    finally:

        cursor.close()

        conn.close()


# =====================================================
# UPDATE GPS
# =====================================================

@shipper_bp.route(
    "/location",
    methods=["POST"]
)
def update_location():

    if not check_shipper():

        return jsonify({
            "success": False,
            "message": "Không có quyền"
        }), 403


    user_id = session.get("user_id")


    data = request.get_json() or {}


    latitude = data.get("latitude")

    longitude = data.get("longitude")


    if latitude is None or longitude is None:

        return jsonify({
            "success": False,
            "message": "Thiếu thông tin GPS"
        }), 400


    conn = get_connection()

    cursor = conn.cursor()


    try:

        cursor.execute(
            """
            SELECT IsWorking

            FROM Users

            WHERE UserID = ?
            """,
            (
                user_id,
            )
        )


        working = cursor.fetchone()


        if (
            not working
            or working[0] == 0
        ):

            return jsonify({
                "success": False,
                "message": "Shipper đang nghỉ ca"
            }), 400


        cursor.execute(
            """
            INSERT INTO DriverLocations
            (
                DriverID,
                Latitude,
                Longitude,
                UpdatedAt
            )

            VALUES
            (
                ?,
                ?,
                ?,
                GETDATE()
            )
            """,
            (
                user_id,
                latitude,
                longitude
            )
        )


        conn.commit()


        return jsonify({
            "success": True
        })


    finally:

        cursor.close()

        conn.close()