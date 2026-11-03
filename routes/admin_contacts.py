from __future__ import annotations

from datetime import datetime
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


admin_contacts_bp = Blueprint(
    "admin_contacts",
    __name__,
    url_prefix="/admin",
)


ALLOWED_STATUSES: set[str] = {
    "Mới",
    "Đang xử lý",
    "Đã phản hồi",
}


ALLOWED_SUBJECTS: set[str] = {
    "Góp ý món ăn",
    "Phản ánh đơn hàng",
    "Hỗ trợ giao hàng",
    "Thanh toán",
    "Hợp tác",
    "Khác",
}


# =========================================================
# CHECK ADMIN
# =========================================================

def check_admin() -> bool:
    """Kiểm tra session hiện tại có phải Admin không."""

    return session.get("role") == "Admin"


# =========================================================
# FORMAT DATETIME
# =========================================================

def format_datetime(
    value: Any,
) -> str:
    """Định dạng datetime để trả về JSON."""

    if not value:
        return ""

    if isinstance(
        value,
        datetime,
    ):
        return value.strftime(
            "%d/%m/%Y %H:%M"
        )

    return str(
        value
    )


# =========================================================
# CONTACT LIST
# =========================================================

@admin_contacts_bp.route(
    "/contacts"
)
def contacts() -> str | Response:
    """Hiển thị danh sách liên hệ khách hàng."""

    if not check_admin():

        return redirect(
            url_for(
                "login"
            )
        )


    # =====================================================
    # FILTER INPUT
    # =====================================================

    selected_status = (
        request.args.get(
            "status"
        )
        or ""
    ).strip()


    selected_subject = (
        request.args.get(
            "subject"
        )
        or ""
    ).strip()


    keyword = (
        request.args.get(
            "q"
        )
        or ""
    ).strip()


    # =====================================================
    # VALIDATE FILTER
    # =====================================================

    if (
        selected_status
        not in
        ALLOWED_STATUSES
    ):

        selected_status = ""


    if (
        selected_subject
        not in
        ALLOWED_SUBJECTS
    ):

        selected_subject = ""


    conn = get_connection()

    cursor = conn.cursor()


    try:

        # =================================================
        # CONTACT SUMMARY
        # =================================================

        cursor.execute(
            """
            SELECT

                COUNT(*)
                    AS TotalContacts,

                SUM(
                    CASE
                        WHEN Status = N'Mới'
                        THEN 1
                        ELSE 0
                    END
                )
                    AS NewContacts,

                SUM(
                    CASE
                        WHEN Status = N'Đang xử lý'
                        THEN 1
                        ELSE 0
                    END
                )
                    AS ProcessingContacts,

                SUM(
                    CASE
                        WHEN Status = N'Đã phản hồi'
                        THEN 1
                        ELSE 0
                    END
                )
                    AS RepliedContacts

            FROM Contacts
            """
        )


        summary = (
            cursor.fetchone()
        )


        if summary:

            total_contacts = (
                summary[0]
                or 0
            )


            new_contacts = (
                summary[1]
                or 0
            )


            processing_contacts = (
                summary[2]
                or 0
            )


            replied_contacts = (
                summary[3]
                or 0
            )


        else:

            total_contacts = 0

            new_contacts = 0

            processing_contacts = 0

            replied_contacts = 0


        # =================================================
        # PENDING ORDERS
        # =================================================

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM Orders

            WHERE Status = N'Đã tiếp nhận'
            """
        )


        pending_row = (
            cursor.fetchone()
        )


        pending_orders = (
            pending_row[0]
            if pending_row
            else 0
        )


        # =================================================
        # ONLINE SHIPPERS
        # =================================================

        cursor.execute(
            """
            SELECT COUNT(*)

            FROM Users

            WHERE Role = 'Shipper'

              AND IsActive = 1

              AND IsWorking = 1
            """
        )


        shipper_row = (
            cursor.fetchone()
        )


        online_shippers = (
            shipper_row[0]
            if shipper_row
            else 0
        )


        # =================================================
        # CONTACT LIST QUERY
        #
        # QUAN TRỌNG:
        # CreatedAt giữ nguyên DATETIME2.
        #
        # Template hiện tại đang dùng:
        #
        # contact.CreatedAt.strftime(...)
        #
        # nên KHÔNG convert CreatedAt thành VARCHAR ở đây.
        # =================================================

        query = """
            SELECT

                c.ContactID,

                c.FullName,

                c.Phone,

                c.Email,

                c.Subject,

                c.OrderCode,

                c.Message,

                c.Status,

                c.AdminNote,

                c.CreatedAt,

                c.UpdatedAt,

                c.ResolvedAt,

                o.OrderID,

                o.Status
                    AS OrderStatus

            FROM Contacts c

            LEFT JOIN Orders o

                ON o.OrderCode =
                   c.OrderCode

            WHERE 1 = 1
        """


        params: list[Any] = []


        # =================================================
        # STATUS FILTER
        # =================================================

        if selected_status:

            query += """
                AND c.Status = ?
            """


            params.append(
                selected_status
            )


        # =================================================
        # SUBJECT FILTER
        # =================================================

        if selected_subject:

            query += """
                AND c.Subject = ?
            """


            params.append(
                selected_subject
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
                    c.FullName
                        LIKE ?

                    OR c.Phone
                        LIKE ?

                    OR ISNULL(
                        c.Email,
                        ''
                    )
                        LIKE ?

                    OR ISNULL(
                        c.OrderCode,
                        ''
                    )
                        LIKE ?

                    OR c.Message
                        LIKE ?
                )
            """


            params.extend(
                [
                    like_keyword,
                    like_keyword,
                    like_keyword,
                    like_keyword,
                    like_keyword,
                ]
            )


        # =================================================
        # ORDER
        # =================================================

        query += """
            ORDER BY

                CASE c.Status

                    WHEN N'Mới'
                    THEN 0

                    WHEN N'Đang xử lý'
                    THEN 1

                    ELSE 2

                END,

                c.CreatedAt DESC,

                c.ContactID DESC
        """


        # =================================================
        # EXECUTE QUERY
        # =================================================

        if params:

            cursor.execute(
                query,
                *params,
            )

        else:

            cursor.execute(
                query
            )


        contact_rows = (
            cursor.fetchall()
        )


    finally:

        cursor.close()

        conn.close()


    # =====================================================
    # RENDER
    # =====================================================

    return render_template(

        "admin/contacts.html",

        contacts=contact_rows,

        username=(
            session.get(
                "fullname"
            )
            or
            "Admin"
        ),

        total_contacts=(
            total_contacts
        ),

        new_contacts=(
            new_contacts
        ),

        processing_contacts=(
            processing_contacts
        ),

        replied_contacts=(
            replied_contacts
        ),

        pending_orders=(
            pending_orders
        ),

        online_shippers=(
            online_shippers
        ),

        selected_status=(
            selected_status
        ),

        selected_subject=(
            selected_subject
        ),

        keyword=keyword,
    )


# =========================================================
# CONTACT DETAIL
# =========================================================

@admin_contacts_bp.route(
    "/contacts/<int:contact_id>",
    methods=["GET"],
)
def contact_detail(
    contact_id: int,
) -> Response | tuple[Response, int]:
    """Lấy chi tiết một liên hệ."""

    if not check_admin():

        return jsonify({

            "success":
                False,

            "message":
                "Không có quyền.",

        }), 403


    conn = get_connection()

    cursor = conn.cursor()


    try:

        cursor.execute(
            """
            SELECT

                c.ContactID,

                c.FullName,

                c.Phone,

                c.Email,

                c.Subject,

                c.OrderCode,

                c.Message,

                c.Status,

                c.AdminNote,

                c.CreatedAt,

                c.UpdatedAt,

                c.ResolvedAt,

                o.OrderID,

                o.Status,

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
                )
                    AS FinalMoney

            FROM Contacts c

            LEFT JOIN Orders o

                ON o.OrderCode =
                   c.OrderCode

            WHERE c.ContactID = ?
            """,
            (
                contact_id,
            ),
        )


        row = (
            cursor.fetchone()
        )


        if not row:

            return jsonify({

                "success":
                    False,

                "message":
                    "Không tìm thấy liên hệ.",

            }), 404


        return jsonify({

            "success":
                True,

            "contact": {

                "id":
                    row[0],

                "fullName":
                    row[1]
                    or "",

                "phone":
                    row[2]
                    or "",

                "email":
                    row[3]
                    or "",

                "subject":
                    row[4]
                    or "",

                "orderCode":
                    row[5]
                    or "",

                "message":
                    row[6]
                    or "",

                "status":
                    row[7]
                    or "Mới",

                "adminNote":
                    row[8]
                    or "",

                "createdAt":
                    format_datetime(
                        row[9]
                    ),

                "updatedAt":
                    format_datetime(
                        row[10]
                    ),

                "resolvedAt":
                    format_datetime(
                        row[11]
                    ),

                "orderId":
                    row[12],

                "orderStatus":
                    row[13]
                    or "",

                "finalMoney":
                    float(
                        row[14]
                        or 0
                    ),

            },

        })


    finally:

        cursor.close()

        conn.close()


# =========================================================
# UPDATE CONTACT STATUS
# =========================================================

@admin_contacts_bp.route(
    "/contacts/<int:contact_id>/status",
    methods=["POST"],
)
def update_contact_status(
    contact_id: int,
) -> Response | tuple[Response, int]:
    """Cập nhật trạng thái và ghi chú nội bộ."""

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


    new_status = (
        data.get(
            "status"
        )
        or ""
    ).strip()


    admin_note = (
        data.get(
            "adminNote"
        )
        or ""
    ).strip()


    # =====================================================
    # VALIDATE STATUS
    # =====================================================

    if (
        new_status
        not in
        ALLOWED_STATUSES
    ):

        return jsonify({

            "success":
                False,

            "message":
                "Trạng thái không hợp lệ.",

        }), 400


    # =====================================================
    # VALIDATE NOTE
    # =====================================================

    if (
        len(
            admin_note
        )
        >
        1000
    ):

        return jsonify({

            "success":
                False,

            "message":
                "Ghi chú tối đa 1000 ký tự.",

        }), 400


    conn = get_connection()

    cursor = conn.cursor()


    try:

        # =================================================
        # CHECK CONTACT
        # =================================================

        cursor.execute(
            """
            SELECT
                ContactID

            FROM Contacts

            WHERE ContactID = ?
            """,
            (
                contact_id,
            ),
        )


        contact = (
            cursor.fetchone()
        )


        if not contact:

            return jsonify({

                "success":
                    False,

                "message":
                    "Không tìm thấy liên hệ.",

            }), 404


        # =================================================
        # UPDATE CONTACT
        # =================================================

        cursor.execute(
            """
            UPDATE Contacts

            SET

                Status = ?,

                AdminNote = ?,

                UpdatedAt =
                    SYSDATETIME(),

                ResolvedAt =

                    CASE

                        WHEN ? =
                             N'Đã phản hồi'

                        THEN
                            SYSDATETIME()

                        ELSE
                            NULL

                    END

            WHERE ContactID = ?
            """,
            (
                new_status,

                admin_note
                or None,

                new_status,

                contact_id,
            ),
        )


        conn.commit()


        return jsonify({

            "success":
                True,

            "status":
                new_status,

            "message":
                "Cập nhật liên hệ thành công.",

        })


    except Exception as error:

        conn.rollback()


        print(
            "LỖI UPDATE CONTACT:",
            error,
        )


        return jsonify({

            "success":
                False,

            "message":
                "Không thể cập nhật liên hệ.",

        }), 500


    finally:

        cursor.close()

        conn.close()