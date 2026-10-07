
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify
)
from decimal import Decimal
import time
from routes.product import product_bp
from database import get_connection
from routes.admin import admin_bp
from routes.shipper import shipper_bp

app = Flask(__name__)

app.secret_key = "bun_cha_secret_key"

app.register_blueprint(product_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(shipper_bp)

@app.route("/")
def home():

    return render_template("index.html")



@app.route("/login", methods=["GET", "POST"])
def login():


    if request.method == "GET":

        return render_template("login.html")



    try:

        data = request.get_json()

        if not data:

            return jsonify({
                "success": False,
                "message": "Không nhận được dữ liệu đăng nhập!"
            }), 400


        username = data.get("username")
        password = data.get("password")


        # -------------------------------------------------
        # KIỂM TRA DỮ LIỆU
        # -------------------------------------------------

        if not username or not password:

            return jsonify({
                "success": False,
                "message": "Vui lòng nhập đầy đủ tài khoản và mật khẩu!"
            }), 400

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                UserID,
                Username,
                Password,
                FullName,
                Role
            FROM Users
            WHERE Username = ?
              AND Password = ?
              AND IsActive = 1
        """, (
            username,
            password
        ))


        user = cursor.fetchone()


        cursor.close()
        conn.close()

        if not user:

            return jsonify({
                "success": False,
                "message": "Tên đăng nhập hoặc mật khẩu không chính xác!"
            }), 401


        session["user_id"] = user.UserID

        session["username"] = user.Username

        session["fullname"] = user.FullName

        session["role"] = user.Role

        return jsonify({
            "success": True,
            "role": user.Role,
            "fullname": user.FullName
        })


    except Exception as e:

        print("LỖI LOGIN:", e)

        return jsonify({
            "success": False,
            "message": "Không thể kết nối tới máy chủ!"
        }), 500

@app.route('/contact')
def contact():

    return render_template("contact.html")

@app.route('/about')
def about():
    return render_template('about.html')

@app.route("/staff/orders")
def staff_orders():

    # -----------------------------------------------------
    # ADMIN VÀ STAFF ĐỀU ĐƯỢC VÀO
    # -----------------------------------------------------

    if session.get("role") not in ["Admin", "Staff"]:

        return redirect(
            url_for("login")
        )


    return render_template(
        "staff_orders.html",
        username=session.get("fullname")
    )



@app.route("/api/session")
def check_session():

    # -----------------------------------------------------
    # CHƯA ĐĂNG NHẬP
    # -----------------------------------------------------

    if "user_id" not in session:

        return jsonify({
            "logged_in": False
        })



    return jsonify({
        "logged_in": True,
        "user_id": session.get("user_id"),
        "username": session.get("username"),
        "fullname": session.get("fullname"),
        "role": session.get("role")
    })

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


@app.errorhandler(404)
def page_not_found(error):

    return """
        <h1>404 - Không tìm thấy trang</h1>
        <p>Đường dẫn bạn truy cập không tồn tại.</p>
    """, 404


@app.errorhandler(500)
def server_error(error):

    return """
        <h1>500 - Lỗi máy chủ</h1>
        <p>Máy chủ đang gặp lỗi. Vui lòng thử lại.</p>
    """, 500

@app.route("/checkout")
def checkout():

    return render_template(
        "checkout.html"
    )

@app.route("/track-order")
def track_order():

    return render_template(
        "track_order.html"
    )



@app.route("/api/orders", methods=["POST"])
def create_order():

    data = request.json

    conn = get_connection()

    cursor = conn.cursor()


    order_code = "BCV" + str(
        int(time.time())
    )[-6:]


    total_money = sum(
        x["price"] * x["quantity"]
        for x in data["products"]
    )


    cursor.execute("""

    INSERT INTO Orders
    (
        OrderCode,
        CustomerName,
        Phone,
        Address,
        Latitude,
        Longitude,
        Note,
        TotalMoney,
        ShippingFee,
        Status
    )

    VALUES(?,?,?,?,?,?,?,?,?,?)

    """,

    (
        order_code,
        data["customerName"],
        data["phone"],
        data["address"],
        data["latitude"],
        data["longitude"],
        data["note"],
        total_money,
        data["shippingFee"],
        "Đã tiếp nhận"
    ))


    conn.commit()

    cursor.close()
    conn.close()


    return jsonify({

        "success": True,

        "orderCode": order_code

    })


@app.route("/api/orders/<phone>")
def get_orders(phone):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT

                o.OrderID,
                o.OrderCode,
                o.CustomerName,
                o.Phone,
                o.Address,

                o.Latitude,
                o.Longitude,

                o.TotalMoney,
                o.ShippingFee,

                o.Status,

                o.CreatedAt,

                o.DriverID,

                u.FullName AS DriverName


            FROM Orders o


            LEFT JOIN Users u

            ON o.DriverID = u.UserID


            WHERE o.Phone = ?


            ORDER BY o.OrderID DESC

        """,
                       (phone,))


        orders = cursor.fetchall()


        result = []

        for order in orders:
            food_total = Decimal(order.TotalMoney or 0)

            shipping_fee = Decimal(order.ShippingFee or 0)

            result.append({

                "code":
                    order.OrderCode,

                "name":
                    order.CustomerName,

                "address":
                    order.Address,

                "foodTotal":
                    float(food_total),

                "shippingFee":
                    float(shipping_fee),

                "total":
                    float(
                        food_total + shipping_fee
                    ),

                "status":
                    order.Status,

                "createdAt":

                    order.CreatedAt.strftime(
                        "%d/%m/%Y %H:%M"
                    )
                    if order.CreatedAt
                    else "",
                "latitude":
                    order.Latitude,

                "longitude":
                    order.Longitude,

                "driverName":
                    order.DriverName

            })


        return jsonify(result)



    except Exception as e:

        print(
            "LỖI TRA CỨU ĐƠN:",
            e
        )

        return jsonify({

            "success":False,

            "message":
            str(e)

        }),500



    finally:

        cursor.close()

        conn.close()

@app.route(
"/api/admin/orders/update/<int:id>",
methods=["POST"]
)
def update_order(id):


    data = request.json


    status = data.get("status")



    conn = get_connection()

    cursor = conn.cursor()



    cursor.execute("""

        UPDATE Orders

        SET Status=?

        WHERE OrderID=?

    """,
    (
        status,
        id
    ))



    conn.commit()


    cursor.close()

    conn.close()



    return jsonify({

        "success":True

    })


@app.route(
    "/api/driver/location",
    methods=["POST"]
)
def update_driver_location():

    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Chưa đăng nhập!"
        }), 401


    if session.get("role") != "Shipper":
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


    driver_id = session.get("user_id")


    conn = get_connection()
    cursor = conn.cursor()


    try:

        cursor.execute("""
            INSERT INTO DriverLocations
            (
                DriverID,
                Latitude,
                Longitude,
                UpdatedAt
            )

            VALUES (?, ?, ?, GETDATE())
        """, (
            driver_id,
            latitude,
            longitude
        ))


        conn.commit()


        return jsonify({
            "success": True
        })


    except Exception as e:

        conn.rollback()

        print(
            "LỖI GPS SHIPPER:",
            e
        )


        return jsonify({
            "success": False,
            "message": "Không thể lưu vị trí!"
        }), 500


    finally:

        cursor.close()
        conn.close()


# =========================================================
# CHẠY SERVER
# =========================================================

if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )