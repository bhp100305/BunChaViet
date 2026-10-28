from __future__ import annotations

from typing import Any

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


admin_payments_bp = Blueprint(
    "admin_payments",
    __name__,
    url_prefix="/admin",
)


# =========================================================
# CONSTANTS
# =========================================================

ALLOWED_METHODS: set[str] = {
    "CASH",
    "BANK_TRANSFER",
}


ALLOWED_STATUSES: set[str] = {
    "Thanh toán khi nhận hàng",
    "Chờ khách chuyển khoản",
    "Khách báo đã chuyển khoản",
    "Đã thanh toán",
    "Đã thu tiền",
}


# =========================================================
# ADMIN CHECK
# =========================================================

def check_admin() -> bool:
    """Kiểm tra tài khoản hiện tại có phải Admin không."""

    return (
        session.get("role")
        ==
        "Admin"
    )


# =========================================================
# PAYMENT PAGE
# =========================================================

@admin_payments_bp.route(
    "/payments"
)
def payments() -> str | Response:
    """Trang quản lý thanh toán."""

    if not check_admin():

        return redirect(
            url_for(
                "login"
            )
        )


    # =====================================================
    # FILTER
    # =====================================================

    selected_method = (
        request.args.get(
            "method"
        )
        or ""
    ).strip().upper()


    selected_status = (
        request.args.get(
            "status"
        )
        or ""
    ).strip()


    keyword = (
        request.args.get(
            "q"
        )
        or ""
    ).strip()


    if (
        selected_method
        not in
        ALLOWED_METHODS
    ):

        selected_method = ""


    if (
        selected_status
        not in
        ALLOWED_STATUSES
    ):

        selected_status = ""


    conn = get_connection()

    cursor = conn.cursor()


    try:

        # =================================================
        # PAYMENT SUMMARY
        # =================================================

        cursor.execute(
            """
            SELECT

                COUNT(*)
                    AS TotalCount,

                SUM(
                    CASE

                        WHEN PaymentMethod =
                             'BANK_TRANSFER'

                        AND PaymentStatus =
                            N'Khách báo đã chuyển khoản'

                        THEN 1

                        ELSE 0

                    END
                )
                    AS ReportedCount,

                SUM(
                    CASE

                        WHEN PaymentStatus IN
                        (
                            N'Đã thanh toán',
                            N'Đã thu tiền'
                        )

                        THEN 1

                        ELSE 0

                    END
                )
                    AS PaidCount,

                SUM(
                    CASE

                        WHEN PaymentMethod =
                             'CASH'

                        AND PaymentStatus =
                            N'Thanh toán khi nhận hàng'

                        THEN 1

                        ELSE 0

                    END
                )
                    AS CashPendingCount

            FROM Orders

            WHERE PaymentMethod
                  IS NOT NULL
            """
        )


        summary = (
            cursor.fetchone()
        )


        total_count = int(
            (
                summary[0]
                if summary
                else 0
            )
            or 0
        )


        reported_count = int(
            (
                summary[1]
                if summary
                else 0
            )
            or 0
        )


        paid_count = int(
            (
                summary[2]
                if summary
                else 0
            )
            or 0
        )


        cash_pending_count = int(
            (
                summary[3]
                if summary
                else 0
            )
            or 0
        )


        # =================================================
        # NEW CONTACT COUNT
        # DÙNG CHO SIDEBAR
        # =================================================

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM Contacts

            WHERE Status = N'Mới'
            """
        )


        contact_row = (
            cursor.fetchone()
        )


        new_contacts = int(
            (
                contact_row[0]
                if contact_row
                else 0
            )
            or 0
        )


        # =================================================
        # PAYMENT LIST
        # =================================================

        query = """
            SELECT

                OrderID,

                OrderCode,

                CustomerName,

                Phone,

                Status
                    AS OrderStatus,

                ISNULL(
                    TotalMoney,
                    0
                )
                    AS TotalMoney,

                ISNULL(
                    ShippingFee,
                    0
                )
                    AS ShippingFee,

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
                )
                    AS FinalMoney,

                PaymentMethod,

                PaymentStatus,

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
                )
                    AS CreatedTime,

                CASE

                    WHEN PaymentReportedAt
                         IS NULL

                    THEN NULL

                    ELSE

                        (
                            CONVERT(
                                VARCHAR(10),
                                PaymentReportedAt,
                                103
                            )
                            +
                            ' '
                            +
                            LEFT(
                                CONVERT(
                                    VARCHAR(8),
                                    PaymentReportedAt,
                                    108
                                ),
                                5
                            )
                        )

                END
                    AS ReportedTime,

                CASE

                    WHEN PaidAt
                         IS NULL

                    THEN NULL

                    ELSE

                        (
                            CONVERT(
                                VARCHAR(10),
                                PaidAt,
                                103
                            )
                            +
                            ' '
                            +
                            LEFT(
                                CONVERT(
                                    VARCHAR(8),
                                    PaidAt,
                                    108
                                ),
                                5
                            )
                        )

                END
                    AS PaidTime

            FROM Orders

            WHERE PaymentMethod
                  IS NOT NULL
        """


        params: list[Any] = []


        # =================================================
        # METHOD FILTER
        # =================================================

        if selected_method:

            query += """
                AND PaymentMethod = ?
            """


            params.append(
                selected_method
            )


        # =================================================
        # STATUS FILTER
        # =================================================

        if selected_status:

            query += """
                AND PaymentStatus = ?
            """


            params.append(
                selected_status
            )


        # =================================================
        # SEARCH
        # =================================================

        if keyword:

            like_keyword = (
                f"%{keyword}%"
            )


            query += """
                AND
                (
                    OrderCode LIKE ?

                    OR CustomerName LIKE ?

                    OR Phone LIKE ?
                )
            """


            params.extend(
                [
                    like_keyword,
                    like_keyword,
                    like_keyword,
                ]
            )


        query += """
            ORDER BY

                CASE

                    WHEN PaymentStatus =
                         N'Khách báo đã chuyển khoản'

                    THEN 0

                    WHEN PaymentStatus =
                         N'Thanh toán khi nhận hàng'

                    THEN 1

                    ELSE 2

                END,

                OrderID DESC
        """


        if params:

            cursor.execute(
                query,
                *params,
            )

        else:

            cursor.execute(
                query
            )


        payment_rows = (
            cursor.fetchall()
        )


    finally:

        cursor.close()

        conn.close()


    return render_template(

        "admin/payments.html",

        payments=payment_rows,

        username=(
            session.get(
                "fullname"
            )
            or
            "Admin"
        ),

        total_count=(
            total_count
        ),

        reported_count=(
            reported_count
        ),

        paid_count=(
            paid_count
        ),

        cash_pending_count=(
            cash_pending_count
        ),

        new_contacts=(
            new_contacts
        ),

        selected_method=(
            selected_method
        ),

        selected_status=(
            selected_status
        ),

        keyword=keyword,
    )


# =========================================================
# CONFIRM PAYMENT
# =========================================================

@admin_payments_bp.route(
    "/payments/<int:order_id>/confirm",
    methods=["POST"],
)
def confirm_payment(
    order_id: int,
) -> Response | tuple[Response, int]:
    """Admin xác nhận thanh toán của đơn hàng."""

    if not check_admin():

        return jsonify({

            "success":
                False,

            "message":
                "Không có quyền.",

        }), 403


    data = (
        request.get_json(
            silent=True
        )
        or {}
    )


    action = str(
        data.get(
            "action"
        )
        or ""
    ).strip().upper()


    allowed_actions = {

        "CONFIRM_PAID",

        "CONFIRM_CASH_COLLECTED",

    }


    if (
        action
        not in
        allowed_actions
    ):

        return jsonify({

            "success":
                False,

            "message":
                "Thao tác thanh toán không hợp lệ.",

        }), 400


    conn = get_connection()

    cursor = conn.cursor()


    try:

        # =================================================
        # LOCK ORDER
        # =================================================

        cursor.execute(
            """
            SELECT

                PaymentMethod,

                PaymentStatus,

                Status

            FROM Orders
            WITH
            (
                UPDLOCK,
                HOLDLOCK
            )

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

            conn.rollback()


            return jsonify({

                "success":
                    False,

                "message":
                    "Không tìm thấy đơn hàng.",

            }), 404


        payment_method = str(
            order[0]
            or ""
        )


        payment_status = str(
            order[1]
            or ""
        )


        order_status = str(
            order[2]
            or ""
        )


        # =================================================
        # BANK TRANSFER
        # =================================================

        if (
            action
            ==
            "CONFIRM_PAID"
        ):

            if (
                payment_method
                !=
                "BANK_TRANSFER"
            ):

                conn.rollback()


                return jsonify({

                    "success":
                        False,

                    "message":
                        "Đơn hàng này không thanh toán bằng chuyển khoản.",

                }), 400


            if (
                payment_status
                ==
                "Đã thanh toán"
            ):

                conn.rollback()


                return jsonify({

                    "success":
                        True,

                    "message":
                        "Đơn hàng đã được xác nhận thanh toán trước đó.",

                    "paymentStatus":
                        payment_status,

                })


            if (
                payment_status
                !=
                "Khách báo đã chuyển khoản"
            ):

                conn.rollback()


                return jsonify({

                    "success":
                        False,

                    "message":
                        "Khách chưa báo đã chuyển khoản.",

                }), 409


            new_status = (
                "Đã thanh toán"
            )


        # =================================================
        # CASH
        # =================================================

        else:

            if (
                payment_method
                !=
                "CASH"
            ):

                conn.rollback()


                return jsonify({

                    "success":
                        False,

                    "message":
                        "Đơn hàng này không thanh toán bằng tiền mặt.",

                }), 400


            if (
                payment_status
                ==
                "Đã thu tiền"
            ):

                conn.rollback()


                return jsonify({

                    "success":
                        True,

                    "message":
                        "Đơn hàng đã được xác nhận thu tiền trước đó.",

                    "paymentStatus":
                        payment_status,

                })


            if (
                order_status
                !=
                "Hoàn thành"
            ):

                conn.rollback()


                return jsonify({

                    "success":
                        False,

                    "message":
                        "Chỉ xác nhận thu tiền mặt khi đơn đã hoàn thành.",

                }), 409


            new_status = (
                "Đã thu tiền"
            )


        # =================================================
        # UPDATE
        # =================================================

        cursor.execute(
            """
            UPDATE Orders

            SET

                PaymentStatus = ?,

                PaidAt =
                    SYSDATETIME()

            WHERE OrderID = ?
            """,
            (
                new_status,
                order_id,
            ),
        )


        conn.commit()


        return jsonify({

            "success":
                True,

            "message":
                "Đã cập nhật trạng thái thanh toán.",

            "paymentStatus":
                new_status,

        })


    except Exception as error:

        conn.rollback()


        print(
            "LỖI CONFIRM PAYMENT:",
            error,
        )


        return jsonify({

            "success":
                False,

            "message":
                "Không thể cập nhật thanh toán.",

        }), 500


    finally:

        cursor.close()

        conn.close()