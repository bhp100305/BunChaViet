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
# SHIPPER ORDERS PAGE
# =====================================================

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
            Address,
            Note,
            TotalMoney,
            ShippingFee,
            (TotalMoney + ShippingFee) AS FinalMoney,
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

            "message":
            "Không có quyền!"

        }), 403



    data = request.get_json()


    status = data.get("status")



    allowed_status = [

        "Đang chuẩn bị",

        "Đang giao",

        "Hoàn thành"

    ]



    if status not in allowed_status:


        return jsonify({

            "success": False,

            "message":
            "Trạng thái không hợp lệ"

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






# =====================================================
# UPDATE SHIPPER GPS
# =====================================================

@shipper_bp.route(
    "/location",
    methods=["POST"]
)
def update_location():



    if not check_shipper():

        return jsonify({

            "success":False,

            "message":
            "Không có quyền!"

        }),403





    data = request.get_json()



    latitude = data.get("latitude")

    longitude = data.get("longitude")




    if latitude is None or longitude is None:


        return jsonify({

            "success":False,

            "message":
            "Thiếu GPS"

        }),400





    conn = get_connection()

    cursor = conn.cursor()



    cursor.execute("""

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

        session.get("user_id"),

        latitude,

        longitude

    ))



    conn.commit()



    cursor.close()

    conn.close()



    return jsonify({

        "success":True

    })