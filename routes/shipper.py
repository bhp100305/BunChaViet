from datetime import datetime
import hmac
import math
from typing import Any, Final
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
# =========================================================
# SESSION CONSTANTS
# =========================================================
SESSION_OK: Final[str] = "OK"
SESSION_INVALID: Final[str] = "SESSION_INVALID"
SESSION_CONFLICT: Final[str] = "SESSION_CONFLICT"
SHIPPER_LOCKED: Final[str] = "SHIPPER_LOCKED"
ApiResponse = (
    Response
    |
    tuple[
        Response,
        int,
    ]
)
# =========================================================
# NORMALIZE DATE
# =========================================================
def normalize_date(
    value: str | None,
    default_value: str,
) -> str:
    """Chuẩn hóa ngày về YYYY-MM-DD."""
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
# =========================================================
# SINGLE ACTIVE SHIPPER SESSION
# =========================================================
def get_shipper_session_state_with_cursor(
    cursor: Any,
    *,
    lock: bool = False,
) -> tuple[str, Any | None]:
    """
    Kiểm tra phiên Shipper hiện tại.
    Khi lock=True:
    khóa row Users bằng UPDLOCK + HOLDLOCK cho tới khi transaction
    commit/rollback.
    Điều này ngăn một thiết bị cũ cập nhật GPS hoặc trạng thái đơn
    đồng thời với lúc thiết bị mới đăng nhập và thay SessionToken.
    """
    # Lấy token trình duyệt đang giữ để so sánh với token hiện tại trong database.
    if (
        session.get("role")
        !=
        "Shipper"
    ):
        return (
            SESSION_INVALID,
            None,
        )
    user_id = session.get(
        "user_id"
    )
    browser_token = (
        session.get(
            "shipper_session_token"
        )
        or ""
    )
    if (
        not user_id
        or
        not browser_token
    ):
        return (
            SESSION_INVALID,
            None,
        )
    if lock:
        query = """
            SELECT
                IsActive,
                IsWorking,
                ActiveSessionToken
            FROM Users WITH (
                UPDLOCK,
                HOLDLOCK
            )
            WHERE UserID = ?
              AND Role = 'Shipper'
        """
    else:
        query = """
            SELECT
                IsActive,
                IsWorking,
                ActiveSessionToken
            FROM Users
            WHERE UserID = ?
              AND Role = 'Shipper'
        """
    cursor.execute(
        query,
        (
            user_id,
        ),
    )
    shipper = cursor.fetchone()
    if not shipper:
        return (
            SESSION_INVALID,
            None,
        )
    is_active = (
        shipper[0]
        or 0
    )
    if is_active != 1:
        return (
            SHIPPER_LOCKED,
            shipper,
        )
    # Đăng nhập ở máy khác sẽ thay ActiveSessionToken; vì vậy token cũ không khớp.
    database_token = (
        shipper[2]
        or ""
    )
    if not database_token:
        return (
            SESSION_INVALID,
            shipper,
        )
    # So sánh an toàn hai token; không khớp nghĩa là phiên này đã bị máy khác thay.
    token_matches = (
        hmac.compare_digest(
            str(
                database_token
            ),
            str(
                browser_token
            ),
        )
    )
    if not token_matches:
        # Báo cho endpoint để trả SESSION_CONFLICT về frontend.
        return (
            SESSION_CONFLICT,
            shipper,
        )
    return (
        SESSION_OK,
        shipper,
    )
# =========================================================
# GET SESSION STATE
# =========================================================
def get_shipper_session_state() -> str:
    """Kiểm tra phiên Shipper bằng connection riêng."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        state, _ = (
            get_shipper_session_state_with_cursor(
                cursor
            )
        )
        return state
    finally:
        cursor.close()
        conn.close()
# =========================================================
# LEGACY BOOLEAN CHECK
# =========================================================
def check_shipper() -> bool:
    """Giữ lại để tương thích với code cũ."""
    return (
        get_shipper_session_state()
        ==
        SESSION_OK
    )
# =========================================================
# SESSION ERROR
# =========================================================
def shipper_session_error(
    state: str,
) -> tuple[
    Response,
    int,
]:
    """Trả lỗi phiên đăng nhập thống nhất cho frontend."""
    if (
        state
        ==
        SESSION_CONFLICT
    ):
        message = (
            "Tài khoản Shipper này vừa đăng nhập "
            "trên một thiết bị khác. "
            "Phiên hiện tại đã bị ngắt "
            "để tránh xung đột GPS."
        )
    elif (
        state
        ==
        SHIPPER_LOCKED
    ):
        message = (
            "Tài khoản Shipper "
            "đã bị khóa."
        )
    else:
        message = (
            "Phiên đăng nhập Shipper "
            "không còn hợp lệ."
        )
    # Chỉ xóa cookie session của trình duyệt hiện tại.
    session.clear()
    return jsonify({
        "success":
            False,
        "code":
            state,
        "message":
            message,
    }), 401
# =========================================================
# AUTHORIZE MUTATING REQUEST
# =========================================================
def authorize_shipper_mutation(
    conn: Any,
    cursor: Any,
) -> tuple[
    Any | None,
    ApiResponse | None,
]:
    """
    Khóa row Shipper và xác minh token.
    Dùng cho các API có thay đổi database:
    - bật/tắt ca
    - cập nhật đơn
    - báo giao thất bại
    - gửi GPS
    """
    state, shipper = (
        get_shipper_session_state_with_cursor(
            cursor,
            lock=True,
        )
    )
    if (
        state
        !=
        SESSION_OK
    ):
        conn.rollback()
        return (
            None,
            shipper_session_error(
                state
            ),
        )
    return (
        shipper,
        None,
    )
# =========================================================
# REDIRECT INVALID PAGE SESSION
# =========================================================
def redirect_invalid_shipper_session(
    state: str,
) -> Response:
    """Redirect trang HTML khi phiên Shipper không còn hợp lệ."""
    session.clear()
    if (
        state
        ==
        SESSION_CONFLICT
    ):
        return redirect(
            url_for(
                "login",
                reason="session_conflict",
            )
        )
    if (
        state
        ==
        SHIPPER_LOCKED
    ):
        return redirect(
            url_for(
                "login",
                reason="account_locked",
            )
        )
    return redirect(
        url_for(
            "login"
        )
    )
# =========================================================
# SESSION HEARTBEAT
# =========================================================
@shipper_bp.route(
    "/session-status"
)
def session_status() -> ApiResponse:
    """
    Frontend gọi định kỳ để phát hiện tài khoản
    đã được đăng nhập trên thiết bị khác.
    """
    # Endpoint heartbeat mà trang shipper gọi định kỳ để biết token có bị thay không.
    state = (
        get_shipper_session_state()
    )
    if (
        state
        !=
        SESSION_OK
    ):
        return shipper_session_error(
            state
        )
    return jsonify({
        "success":
            True,
        "code":
            SESSION_OK,
    })
# =========================================================
# SHIPPER DASHBOARD
# =========================================================
@shipper_bp.route(
    "/orders"
)
def orders() -> str | Response:
    """Trang quản lý đơn của Shipper."""
    session_state = (
        get_shipper_session_state()
    )
    if (
        session_state
        !=
        SESSION_OK
    ):
        return redirect_invalid_shipper_session(
            session_state
        )
    user_id = session.get(
        "user_id"
    )
    today = (
        datetime.now().strftime(
            "%Y-%m-%d"
        )
    )
    # =====================================================
    # DATE FILTER
    # =====================================================
    old_date = (
        request.args.get(
            "date"
        )
    )
    from_date = (
        normalize_date(
            (
                request.args.get(
                    "from_date"
                )
                or
                old_date
            ),
            today,
        )
    )
    to_date = (
        normalize_date(
            (
                request.args.get(
                    "to_date"
                )
                or
                old_date
                or
                from_date
            ),
            from_date,
        )
    )
    if (
        from_date
        >
        to_date
    ):
        from_date, to_date = (
            to_date,
            from_date,
        )
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # =================================================
        # SHIPPER INFO
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
        shipper = (
            cursor.fetchone()
        )
        if not shipper:
            session.clear()
            return redirect(
                url_for(
                    "login"
                )
            )
        is_working = (
            shipper[0]
            or 0
        )
        # =================================================
        # OVERVIEW STATISTICS
        # =================================================
        cursor.execute(
            """
            SELECT
                COUNT(*),
                SUM(
                    CASE
                        WHEN
                            CAST(
                                ISNULL(
                                    DeliveredAt,
                                    CreatedAt
                                )
                                AS DATE
                            )
                            =
                            CAST(
                                GETDATE()
                                AS DATE
                            )
                        THEN 1
                        ELSE 0
                    END
                ),
                SUM(
                    CASE
                        WHEN
                            YEAR(
                                ISNULL(
                                    DeliveredAt,
                                    CreatedAt
                                )
                            )
                            =
                            YEAR(
                                GETDATE()
                            )
                        AND
                            MONTH(
                                ISNULL(
                                    DeliveredAt,
                                    CreatedAt
                                )
                            )
                            =
                            MONTH(
                                GETDATE()
                            )
                        THEN 1
                        ELSE 0
                    END
                )
            FROM Orders
            WHERE DriverID = ?
              AND Status =
                  N'Hoàn thành'
            """,
            (
                user_id,
            ),
        )
        statistic = (
            cursor.fetchone()
        )
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
        # ACTIVE ORDERS COUNT
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
        # ALL SHIPPER ORDERS
        #
        # INDEX ORDER:
        #
        # 0  OrderID
        # 1  OrderCode
        # 2  CustomerName
        # 3  Phone
        # 4  Address
        # 5  Note
        # 6  TotalMoney
        # 7  ShippingFee
        # 8  FinalMoney
        # 9  Status
        # 10 CreatedTime
        # 11 CustomerLatitude
        # 12 CustomerLongitude
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
                CASE
                    WHEN CreatedAt IS NULL
                    THEN ''
                    ELSE
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
                END AS CreatedTime,
                Latitude
                    AS CustomerLatitude,
                Longitude
                    AS CustomerLongitude
            FROM Orders
            WHERE DriverID = ?
            ORDER BY
                OrderID DESC
            """,
            (
                user_id,
            ),
        )
        order_rows = (
            cursor.fetchall()
        )
        # =================================================
        # RANGE STATISTICS
        # =================================================
        cursor.execute(
            """
            SELECT
                COUNT(*)
                    AS CompletedCount,
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
                )
                    AS CollectedMoney
            FROM Orders
            WHERE DriverID = ?
              AND Status =
                  N'Hoàn thành'
              AND
                  CAST(
                      ISNULL(
                          DeliveredAt,
                          CreatedAt
                      )
                      AS DATE
                  )
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
        # COMPLETED ORDERS IN RANGE
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
                CASE
                    WHEN
                        ISNULL(
                            DeliveredAt,
                            CreatedAt
                        )
                        IS NULL
                    THEN ''
                    ELSE
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
                END AS CompletedTime
            FROM Orders
            WHERE DriverID = ?
              AND Status =
                  N'Hoàn thành'
              AND
                  CAST(
                      ISNULL(
                          DeliveredAt,
                          CreatedAt
                      )
                      AS DATE
                  )
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
        # FAILED ORDERS
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
        orders=order_rows,
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
# =========================================================
# TOGGLE WORK
# =========================================================
@shipper_bp.route(
    "/toggle-work",
    methods=[
        "POST",
    ],
)
def toggle_work() -> ApiResponse:
    """Bật hoặc tắt trạng thái nhận đơn."""
    user_id = (
        session.get(
            "user_id"
        )
    )
    conn = get_connection()
    cursor = conn.cursor()
    try:
        shipper, auth_error = (
            authorize_shipper_mutation(
                conn,
                cursor,
            )
        )
        if auth_error:
            return auth_error
        is_working = (
            shipper[1]
            or 0
        )
        # =================================================
        # MUỐN NGHỈ CA
        # =================================================
        if (
            is_working
            ==
            1
        ):
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
            if (
                unfinished
                >
                0
            ):
                conn.rollback()
                return jsonify({
                    "success":
                        False,
                    "message":
                        f"Bạn còn {unfinished} đơn "
                        "chưa xử lý xong. "
                        "Hãy xử lý đơn trước khi nghỉ ca.",
                }), 400
        new_status = (
            0
            if
            is_working == 1
            else
            1
        )
        cursor.execute(
            """
            UPDATE Users
            SET IsWorking = ?
            WHERE UserID = ?
              AND Role =
                  'Shipper'
            """,
            (
                new_status,
                user_id,
            ),
        )
        conn.commit()
        return jsonify({
            "success":
                True,
            "working":
                new_status,
        })
    finally:
        cursor.close()
        conn.close()
# =========================================================
# UPDATE ORDER STATUS
# =========================================================
@shipper_bp.route(
    "/update/<int:id>",
    methods=[
        "POST",
    ],
)
def update_status(
    id: int,
) -> ApiResponse:
    """Cập nhật trạng thái đơn theo đúng flow Shipper."""
    data = (
        request.get_json(
            silent=True
        )
        or {}
    )
    new_status = (
        str(
            data.get(
                "status"
            )
            or ""
        ).strip()
    )
    user_id = (
        session.get(
            "user_id"
        )
    )
    conn = get_connection()
    cursor = conn.cursor()
    try:
        _, auth_error = (
            authorize_shipper_mutation(
                conn,
                cursor,
            )
        )
        if auth_error:
            return auth_error
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
        order = (
            cursor.fetchone()
        )
        if not order:
            conn.rollback()
            return jsonify({
                "success":
                    False,
                "message":
                    "Không tìm thấy đơn hoặc đơn "
                    "không thuộc về bạn.",
            }), 404
        current_status = (
            order[0]
        )
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
            conn.rollback()
            return jsonify({
                "success":
                    False,
                "message":
                    "Đơn hàng này không thể "
                    "thay đổi trạng thái.",
            }), 400
        if (
            new_status
            !=
            expected_status
        ):
            conn.rollback()
            return jsonify({
                "success":
                    False,
                "message":
                    f"Không thể chuyển từ "
                    f"'{current_status}' sang "
                    f"'{new_status}'.",
            }), 400
        # =================================================
        # COMPLETE
        # =================================================
        if (
            new_status
            ==
            "Hoàn thành"
        ):
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
                  AND Status =
                      N'Đang giao'
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
                  AND Status = ?
                """,
                (
                    new_status,
                    id,
                    user_id,
                    current_status,
                ),
            )
        if (
            cursor.rowcount
            ==
            0
        ):
            conn.rollback()
            return jsonify({
                "success":
                    False,
                "message":
                    "Trạng thái đơn vừa thay đổi. "
                    "Vui lòng tải lại trang.",
            }), 409
        conn.commit()
        return jsonify({
            "success":
                True,
            "message":
                "Cập nhật trạng thái thành công.",
        })
    finally:
        cursor.close()
        conn.close()
# =========================================================
# FAILED DELIVERY
# =========================================================
@shipper_bp.route(
    "/cancel/<int:id>",
    methods=[
        "POST",
    ],
)
def cancel_order(
    id: int,
) -> ApiResponse:
    """Ghi nhận đơn không giao được."""
    data = (
        request.get_json(
            silent=True
        )
        or {}
    )
    reason = (
        data.get(
            "reason"
        )
        or ""
    ).strip()
    shipper_note = (
        data.get(
            "note"
        )
        or ""
    ).strip()
    if not reason:
        return jsonify({
            "success":
                False,
            "message":
                "Bạn cần chọn lý do "
                "không giao được.",
        }), 400
    user_id = (
        session.get(
            "user_id"
        )
    )
    conn = get_connection()
    cursor = conn.cursor()
    try:
        _, auth_error = (
            authorize_shipper_mutation(
                conn,
                cursor,
            )
        )
        if auth_error:
            return auth_error
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
        order = (
            cursor.fetchone()
        )
        if not order:
            conn.rollback()
            return jsonify({
                "success":
                    False,
                "message":
                    "Không tìm thấy đơn hàng.",
            }), 404
        current_status = (
            order[0]
        )
        old_note = (
            order[1]
            or ""
        )
        if (
            current_status
            !=
            "Đang giao"
        ):
            conn.rollback()
            return jsonify({
                "success":
                    False,
                "message":
                    "Chỉ đơn đang giao mới có thể "
                    "báo không giao được.",
            }), 400
        failure_text = (
            "Không giao được: "
            +
            reason
        )
        if shipper_note:
            failure_text += (
                ". Ghi chú shipper: "
                +
                shipper_note
            )
        if old_note:
            updated_note = (
                old_note
                +
                " | "
                +
                failure_text
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
              AND Status =
                  N'Đang giao'
            """,
            (
                updated_note,
                id,
                user_id,
            ),
        )
        if (
            cursor.rowcount
            ==
            0
        ):
            conn.rollback()
            return jsonify({
                "success":
                    False,
                "message":
                    "Trạng thái đơn vừa thay đổi. "
                    "Vui lòng tải lại trang.",
            }), 409
        conn.commit()
        return jsonify({
            "success":
                True,
            "message":
                "Đã ghi nhận đơn không giao được.",
        })
    finally:
        cursor.close()
        conn.close()
# =========================================================
# UPDATE GPS
# =========================================================
@shipper_bp.route(
    "/location",
    methods=[
        "POST",
    ],
)
def update_location() -> ApiResponse:
    """
    Nhận GPS của thiết bị Shipper đang active.
    Quan trọng:
    request được khóa trên row Users để tránh thiết bị cũ
    và thiết bị mới cùng ghi GPS trong lúc SessionToken đổi.
    """
    data = (
        request.get_json(
            silent=True
        )
        or {}
    )
    latitude_raw = (
        data.get(
            "latitude"
        )
    )
    longitude_raw = (
        data.get(
            "longitude"
        )
    )
    if (
        latitude_raw
        is None
        or
        longitude_raw
        is None
    ):
        return jsonify({
            "success":
                False,
            "message":
                "Thiếu dữ liệu GPS.",
        }), 400
    # =====================================================
    # VALIDATE GPS
    # =====================================================
    try:
        latitude = float(
            latitude_raw
        )
        longitude = float(
            longitude_raw
        )
    except (
        TypeError,
        ValueError,
    ):
        return jsonify({
            "success":
                False,
            "message":
                "Tọa độ GPS không hợp lệ.",
        }), 400
    if (
        not math.isfinite(
            latitude
        )
        or
        not math.isfinite(
            longitude
        )
    ):
        return jsonify({
            "success":
                False,
            "message":
                "Tọa độ GPS không hợp lệ.",
        }), 400
    if (
        latitude < -90
        or
        latitude > 90
        or
        longitude < -180
        or
        longitude > 180
    ):
        return jsonify({
            "success":
                False,
            "message":
                "Tọa độ GPS nằm ngoài phạm vi hợp lệ.",
        }), 400
    user_id = (
        session.get(
            "user_id"
        )
    )
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # =================================================
        # KHÓA USER ROW + KIỂM TRA SESSION TOKEN
        # =================================================
        shipper, auth_error = (
            authorize_shipper_mutation(
                conn,
                cursor,
            )
        )
        if auth_error:
            return auth_error
        is_working = (
            shipper[1]
            or 0
        )
        if (
            is_working
            !=
            1
        ):
            conn.rollback()
            return jsonify({
                "success":
                    False,
                "message":
                    "Shipper đang nghỉ ca.",
            }), 400
        # =================================================
        # INSERT GPS
        # =================================================
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
            "success":
                True,
        })
    finally:
        cursor.close()
        conn.close()
