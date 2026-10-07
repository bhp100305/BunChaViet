from datetime import datetime

from flask import (
    Blueprint,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from database import get_connection


shipper_bp = Blueprint(
    "shipper",
    __name__,
    url_prefix="/shipper",
)


# =====================================================
# CHECK ROLE
# =====================================================

def check_shipper() -> bool:
    """Kiểm tra người dùng hiện tại có phải shipper hay không."""
    return session.get("role") == "Shipper"


# =====================================================
# NORMALIZE DATE
# =====================================================

def normalize_date(
    value: str | None,
    default_value: str,
) -> str:
    """Chuẩn hóa ngày theo định dạng YYYY-MM-DD."""

    if not value:
        return default_value

    try:
        datetime.strptime(
            value,
            "%Y-%m-%d",
        )

        return value

    except ValueError:
        return default_value


# =====================================================
# SHIPPER DASHBOARD
# =====================================================

@shipper_bp.route("/orders")
def orders() -> str | Response:

    if not check_shipper():
        return redirect(
            url_for("login")
        )

    user_id = session.get("user_id")

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    # =================================================
    # HỖ TRỢ URL CŨ
    #
    # ?date=2026-09-30
    #
    # VÀ URL MỚI
    #
    # ?from_date=2026-09-01&to_date=2026-09-30
    # =================================================

    old_date = request.args.get(
        "date"
    )

    from_date = normalize_date(
        request.args.get("from_date")
        or old_date,
        today,
    )

    to_date = normalize_date(
        request.args.get("to_date")
        or old_date
        or from_date,
        from_date,
    )

    if from_date > to_date:
        from_date, to_date = (
            to_date,
            from_date,
        )

    conn = get_connection()
    cursor = conn.cursor()

    try:

        # =================================================
        # THÔNG TIN SHIPPER
        # =================================================

        cursor.execute(
            """
            SELECT
                IsWorking,
                IsActive

            FROM Users

            WHERE UserID = ?
              AND Role = 'Shipper'
            """,
            (
                user_id,
            ),
        )

        shipper = cursor.fetchone()

        if not shipper:
            session.clear()

            return redirect(
                url_for("login")
            )

        is_working = (
            shipper[0]
            or 0
        )

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
                        CAST(
                            GETDATE()
                        AS DATE)

                        THEN 1

                        ELSE 0

                    END
                ),

                SUM(
                    CASE

                        WHEN YEAR(
                            ISNULL(
                                DeliveredAt,
                                CreatedAt
                            )
                        )
                        =
                        YEAR(GETDATE())

                        AND

                        MONTH(
                            ISNULL(
                                DeliveredAt,
                                CreatedAt
                            )
                        )
                        =
                        MONTH(GETDATE())

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
            ),
        )

        statistic = cursor.fetchone()

        total_done = (
            statistic[0]
            or 0
        )

        today_done = (
            statistic[1]
            or 0
        )

        month_done = (
            statistic[2]
            or 0
        )

        # =================================================
        # ĐƠN ĐANG XỬ LÝ
        # =================================================

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
            ),
        )

        active_order_count = (
            cursor.fetchone()[0]
            or 0
        )

        # =================================================
        # TẤT CẢ ĐƠN CỦA SHIPPER
        #
        # QUAN TRỌNG:
        # CreatedAt được convert thành STRING ngay trong SQL.
        # HTML không gọi .strftime() nữa.
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

                (
                    CONVERT(
                        VARCHAR(10),
                        CreatedAt,
                        103
                    )
                    +
                    ' '
                    +
                    LEFT(
                        CONVERT(
                            VARCHAR(8),
                            CreatedAt,
                            108
                        ),
                        5
                    )
                ) AS CreatedTime

            FROM Orders

            WHERE DriverID = ?

            ORDER BY
                OrderID DESC
            """,
            (
                user_id,
            ),
        )

        orders = cursor.fetchall()

        # =================================================
        # THỐNG KÊ TRONG KHOẢNG NGÀY
        # =================================================

        cursor.execute(
            """
            SELECT

                COUNT(*) AS CompletedCount,

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
                ) AS CollectedMoney

            FROM Orders

            WHERE DriverID = ?

              AND Status = N'Hoàn thành'

              AND CAST(
                    ISNULL(
                        DeliveredAt,
                        CreatedAt
                    )
                  AS DATE)

                  BETWEEN

                  CONVERT(
                      DATE,
                      ?,
                      23
                  )

                  AND

                  CONVERT(
                      DATE,
                      ?,
                      23
                  )
            """,
            (
                user_id,
                from_date,
                to_date,
            ),
        )

        range_statistic = (
            cursor.fetchone()
        )

        range_completed_count = (
            range_statistic[0]
            or 0
        )

        range_collected_total = (
            range_statistic[1]
            or 0
        )

        # =================================================
        # DANH SÁCH ĐƠN HOÀN THÀNH
        # TRONG KHOẢNG NGÀY
        #
        # CompletedAt cũng được convert thành STRING.
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

                (
                    CONVERT(
                        VARCHAR(10),
                        ISNULL(
                            DeliveredAt,
                            CreatedAt
                        ),
                        103
                    )
                    +
                    ' '
                    +
                    LEFT(
                        CONVERT(
                            VARCHAR(8),
                            ISNULL(
                                DeliveredAt,
                                CreatedAt
                            ),
                            108
                        ),
                        5
                    )
                ) AS CompletedTime

            FROM Orders

            WHERE DriverID = ?

              AND Status = N'Hoàn thành'

              AND CAST(
                    ISNULL(
                        DeliveredAt,
                        CreatedAt
                    )
                  AS DATE)

                  BETWEEN

                  CONVERT(
                      DATE,
                      ?,
                      23
                  )

                  AND

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
                from_date,
                to_date,
            ),
        )

        statistic_orders = (
            cursor.fetchall()
        )

        # =================================================
        # ĐƠN KHÔNG GIAO ĐƯỢC
        # =================================================

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM Orders

            WHERE DriverID = ?

              AND Status IN
              (
                  N'Không giao được',
                  N'Đã hủy'
              )
            """,
            (
                user_id,
            ),
        )

        failed_order_count = (
            cursor.fetchone()[0]
            or 0
        )

    finally:
        cursor.close()
        conn.close()

    return render_template(
        "shipper/orders.html",

        orders=orders,

        username=session.get(
            "fullname"
        ),

        is_working=is_working,

        total_done=total_done,

        today_done=today_done,

        month_done=month_done,

        active_order_count=(
            active_order_count
        ),

        failed_order_count=(
            failed_order_count
        ),

        from_date=from_date,

        to_date=to_date,

        range_completed_count=(
            range_completed_count
        ),

        range_collected_total=(
            range_collected_total
        ),

        statistic_orders=(
            statistic_orders
        ),
    )


# =====================================================
# BẬT / TẮT CA
# =====================================================

@shipper_bp.route(
    "/toggle-work",
    methods=["POST"],
)
def toggle_work() -> Response | tuple[Response, int]:

    if not check_shipper():

        return jsonify({
            "success": False,
            "message": "Không có quyền.",
        }), 403

    user_id = session.get(
        "user_id"
    )

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            SELECT
                IsWorking,
                IsActive

            FROM Users

            WHERE UserID = ?
              AND Role = 'Shipper'
            """,
            (
                user_id,
            ),
        )

        shipper = cursor.fetchone()

        if not shipper:

            return jsonify({
                "success": False,
                "message":
                    "Không tìm thấy shipper.",
            }), 404

        is_working = (
            shipper[0]
            or 0
        )

        is_active = (
            shipper[1]
            or 0
        )

        if is_active != 1:

            return jsonify({
                "success": False,
                "message":
                    "Tài khoản của bạn đã bị khóa.",
            }), 403

        # =============================================
        # ĐANG LÀM -> MUỐN NGHỈ
        # =============================================

        if is_working == 1:

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
                ),
            )

            unfinished = (
                cursor.fetchone()[0]
                or 0
            )

            if unfinished > 0:

                return jsonify({
                    "success": False,
                    "message":
                        f"Bạn còn {unfinished} đơn "
                        "chưa xử lý xong. "
                        "Hãy xử lý đơn trước khi nghỉ ca.",
                }), 400

        new_status = (
            0
            if is_working == 1
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
                user_id,
            ),
        )

        conn.commit()

        return jsonify({
            "success": True,
            "working": new_status,
        })

    finally:
        cursor.close()
        conn.close()


# =====================================================
# UPDATE ORDER STATUS
# =====================================================

@shipper_bp.route(
    "/update/<int:id>",
    methods=["POST"],
)
def update_status(
    id: int,
) -> Response | tuple[Response, int]:

    if not check_shipper():

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

    new_status = data.get(
        "status"
    )

    user_id = session.get(
        "user_id"
    )

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            SELECT Status

            FROM Orders

            WHERE OrderID = ?

              AND DriverID = ?
            """,
            (
                id,
                user_id,
            ),
        )

        order = cursor.fetchone()

        if not order:

            return jsonify({
                "success": False,
                "message":
                    "Không tìm thấy đơn hoặc đơn "
                    "không thuộc về bạn.",
            }), 404

        current_status = order[0]

        allowed_transitions = {
            "Đã giao shipper":
                "Đang chuẩn bị",

            "Đang chuẩn bị":
                "Đang giao",

            "Đang giao":
                "Hoàn thành",
        }

        expected_status = (
            allowed_transitions.get(
                current_status
            )
        )

        if not expected_status:

            return jsonify({
                "success": False,
                "message":
                    "Đơn hàng này không thể "
                    "thay đổi trạng thái.",
            }), 400

        if (
            new_status
            != expected_status
        ):

            return jsonify({
                "success": False,
                "message":
                    f"Không thể chuyển từ "
                    f"'{current_status}' sang "
                    f"'{new_status}'.",
            }), 400

        if new_status == "Hoàn thành":

            cursor.execute(
                """
                UPDATE Orders

                SET
                    Status =
                        N'Hoàn thành',

                    DeliveredAt =
                        GETDATE()

                WHERE OrderID = ?

                  AND DriverID = ?
                """,
                (
                    id,
                    user_id,
                ),
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
                    new_status,
                    id,
                    user_id,
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


# =====================================================
# KHÔNG GIAO ĐƯỢC
# =====================================================

@shipper_bp.route(
    "/cancel/<int:id>",
    methods=["POST"],
)
def cancel_order(
    id: int,
) -> Response | tuple[Response, int]:

    if not check_shipper():

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

    reason = (
        data.get("reason")
        or ""
    ).strip()

    shipper_note = (
        data.get("note")
        or ""
    ).strip()

    if not reason:

        return jsonify({
            "success": False,
            "message":
                "Bạn cần chọn lý do "
                "không giao được.",
        }), 400

    user_id = session.get(
        "user_id"
    )

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
                user_id,
            ),
        )

        order = cursor.fetchone()

        if not order:

            return jsonify({
                "success": False,
                "message":
                    "Không tìm thấy đơn hàng.",
            }), 404

        current_status = order[0]

        old_note = (
            order[1]
            or ""
        )

        if current_status != "Đang giao":

            return jsonify({
                "success": False,
                "message":
                    "Chỉ đơn đang giao mới có thể "
                    "báo không giao được.",
            }), 400

        failure_text = (
            "Không giao được: "
            + reason
        )

        if shipper_note:

            failure_text += (
                ". Ghi chú shipper: "
                + shipper_note
            )

        if old_note:

            updated_note = (
                old_note
                + " | "
                + failure_text
            )

        else:

            updated_note = (
                failure_text
            )

        cursor.execute(
            """
            UPDATE Orders

            SET
                Status =
                    N'Không giao được',

                Note = ?

            WHERE OrderID = ?

              AND DriverID = ?
            """,
            (
                updated_note,
                id,
                user_id,
            ),
        )

        conn.commit()

        return jsonify({
            "success": True,
            "message":
                "Đã ghi nhận đơn không giao được.",
        })

    finally:
        cursor.close()
        conn.close()


# =====================================================
# UPDATE GPS
# =====================================================

@shipper_bp.route(
    "/location",
    methods=["POST"],
)
def update_location() -> Response | tuple[Response, int]:

    if not check_shipper():

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

    latitude = data.get(
        "latitude"
    )

    longitude = data.get(
        "longitude"
    )

    if (
        latitude is None
        or longitude is None
    ):

        return jsonify({
            "success": False,
            "message":
                "Thiếu dữ liệu GPS.",
        }), 400

    user_id = session.get(
        "user_id"
    )

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            SELECT
                IsWorking,
                IsActive

            FROM Users

            WHERE UserID = ?
            """,
            (
                user_id,
            ),
        )

        shipper = cursor.fetchone()

        if not shipper:

            return jsonify({
                "success": False,
                "message":
                    "Không tìm thấy shipper.",
            }), 404

        if shipper[1] != 1:

            return jsonify({
                "success": False,
                "message":
                    "Tài khoản shipper đã bị khóa.",
            }), 403

        if shipper[0] != 1:

            return jsonify({
                "success": False,
                "message":
                    "Shipper đang nghỉ ca.",
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
                longitude,
            ),
        )

        conn.commit()

        return jsonify({
            "success": True,
        })

    finally:
        cursor.close()
        conn.close()