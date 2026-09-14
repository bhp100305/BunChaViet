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


# =========================================================
# KIỂM TRA SHIPPER
# =========================================================

def check_shipper():

    return session.get("role") == "Shipper"


# =========================================================
# TRANG ĐƠN HÀNG SHIPPER
# =========================================================

@shipper_bp.route("/orders")
def orders():

    if not check_shipper():

        return redirect(
            url_for("login")
        )


    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""
        SELECT
            OrderID,
            OrderCode,
            CustomerName,
            Phone,
            Province,
            District,
            Ward,
            Address,
            Note,
            TotalMoney,
            Status,
            DriverID
        FROM Orders
        WHERE DriverID = ?
        ORDER BY OrderID DESC
    """,
    (
        session.get("user_id"),
    ))


    orders = cursor.fetchall()


    cursor.close()

    conn.close()


    return render_template(
        "shipper/orders.html",
        orders=orders,
        username=session.get("fullname")
    )


# =========================================================
# SHIPPER CẬP NHẬT TRẠNG THÁI
# =========================================================

@shipper_bp.route(
    "/update/<int:id>",
    methods=["POST"]
)
def update_status(id):

    if not check_shipper():

        return jsonify({
            "success": False,
            "message": "Không có quyền!"
        }), 403


    data = request.get_json()

    status = data.get("status")


    allowed_status = [
        "Đang giao",
        "Hoàn thành"
    ]


    if status not in allowed_status:

        return jsonify({
            "success": False,
            "message": "Trạng thái không hợp lệ!"
        }), 400


    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""
        UPDATE Orders

        SET Status = ?

        WHERE OrderID = ?

        AND DriverID = ?
    """,
    (
        status,
        id,
        session.get("user_id")
    ))


    conn.commit()


    cursor.close()

    conn.close()


    return jsonify({
        "success": True
    })


# =========================================================
# SHIPPER GỬI VỊ TRÍ GPS
# =========================================================

@shipper_bp.route(
    "/location",
    methods=["POST"]
)
def update_location():

    if not check_shipper():

        return jsonify({
            "success": False,
            "message": "Không có quyền!"
        }), 403


    data = request.get_json()


    latitude = data.get("latitude")

    longitude = data.get("longitude")


    if latitude is None or longitude is None:

        return jsonify({
            "success": False,
            "message": "Thiếu tọa độ GPS!"
        }), 400


    user_id = session.get("user_id")


    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""
        SELECT UserID
        FROM ShipperLocations
        WHERE UserID = ?
    """,
    (
        user_id,
    ))


    existing = cursor.fetchone()


    if existing:

        cursor.execute("""
            UPDATE ShipperLocations

            SET
                Latitude = ?,
                Longitude = ?,
                UpdatedAt = GETDATE()

            WHERE UserID = ?
        """,
        (
            latitude,
            longitude,
            user_id
        ))


    else:

        cursor.execute("""
            INSERT INTO ShipperLocations
            (
                UserID,
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
        ))


    conn.commit()


    cursor.close()

    conn.close()


    return jsonify({
        "success": True
    })