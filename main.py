
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
import os
import time
import secrets
from routes.product import product_bp
from database import get_connection
from routes.admin import admin_bp
from routes.shipper import shipper_bp
from routes.admin_contacts import admin_contacts_bp
from routes.admin_payments import admin_payments_bp
from routes.email_otp import email_otp_bp
from routes.customer_auth import customer_auth_bp
app = Flask(__name__)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY"
)
print(
    "GMAIL_ADDRESS loaded:",
    bool(os.getenv("GMAIL_ADDRESS"))
)

print(
    "GMAIL_APP_PASSWORD loaded:",
    bool(os.getenv("GMAIL_APP_PASSWORD"))
)

print(
    "OTP_HMAC_SECRET loaded:",
    bool(os.getenv("OTP_HMAC_SECRET"))
)

app.register_blueprint(product_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(shipper_bp)
app.register_blueprint(admin_contacts_bp)
app.register_blueprint(
    admin_payments_bp
)
app.register_blueprint(email_otp_bp)
app.register_blueprint(customer_auth_bp)
@app.route("/")
def home():

    return render_template("index.html")


@app.route(
    "/login",
    methods=[
        "GET",
        "POST",
    ],
)
def login():
    """Đăng nhập và chỉ cho phép một phiên Shipper hoạt động."""

    if request.method == "GET":

        return render_template(
            "login.html"
        )


    conn = None
    cursor = None


    try:

        data = (
            request.get_json(
                silent=True
            )
            or {}
        )


        username = (
            data.get(
                "username"
            )
            or ""
        ).strip()


        password = (
            data.get(
                "password"
            )
            or ""
        )


        if (
            not username
            or
            not password
        ):

            return jsonify({

                "success":
                    False,

                "message":
                    "Vui lòng nhập đầy đủ tài khoản và mật khẩu!",

            }), 400


        conn = get_connection()

        cursor = conn.cursor()


        cursor.execute(
            """
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
            """,
            (
                username,
                password,
            ),
        )


        user = (
            cursor.fetchone()
        )


        if not user:

            return jsonify({

                "success":
                    False,

                "message":
                    "Tên đăng nhập hoặc mật khẩu không chính xác!",

            }), 401


        # =================================================
        # XÓA COOKIE SESSION CŨ CỦA CHÍNH TRÌNH DUYỆT NÀY
        # =================================================

        session.clear()


        session[
            "user_id"
        ] = user.UserID


        session[
            "username"
        ] = user.Username


        session[
            "fullname"
        ] = user.FullName


        session[
            "role"
        ] = user.Role


        # Shipper chỉ được có một phiên hoạt động: mỗi lần đăng nhập tạo token mới.
        # Token trong database sẽ thay token cũ, khiến các thiết bị đăng nhập trước
        # không còn khớp và bị nhận diện là SESSION_CONFLICT ở lần kiểm tra kế tiếp.

        if (
            user.Role
            ==
            "Shipper"
        ):

            # Token khó đoán, đại diện cho phiên đăng nhập trên trình duyệt hiện tại.
            shipper_token = (
                secrets.token_urlsafe(
                    32
                )
            )


            # Lưu token mới làm phiên duy nhất đang hoạt động của tài khoản này.
            cursor.execute(
                """
                UPDATE Users

                SET
                    ActiveSessionToken = ?,

                    SessionUpdatedAt =
                        SYSDATETIME()

                WHERE UserID = ?

                  AND Role =
                      'Shipper'
                """,
                (
                    shipper_token,
                    user.UserID,
                ),
            )


            conn.commit()


            # Lưu cùng token vào cookie session của trình duyệt vừa đăng nhập.
            session[
                "shipper_session_token"
            ] = shipper_token


        return jsonify({

            "success":
                True,

            "role":
                user.Role,

            "fullname":
                user.FullName,

        })


    except Exception as error:

        print(
            "LỖI LOGIN:",
            error,
        )


        return jsonify({

            "success":
                False,

            "message":
                "Không thể kết nối tới máy chủ!",

        }), 500


    finally:

        if (
            cursor
            is not None
        ):

            cursor.close()


        if (
            conn
            is not None
        ):

            conn.close()


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



@app.route(
    "/api/session"
)
def check_session():
    """Kiểm tra session hiện tại."""

    if (
        "user_id"
        not in session
    ):

        return jsonify({

            "logged_in":
                False,

        })


    # =====================================================
    # SHIPPER PHẢI CÓ TOKEN ĐÚNG
    # =====================================================

    if (
        session.get(
            "role"
        )
        ==
        "Shipper"
    ):

        token = (
            session.get(
                "shipper_session_token"
            )
        )


        if not token:

            session.clear()


            return jsonify({

                "logged_in":
                    False,

                "reason":
                    "SESSION_INVALID",

            })


        conn = get_connection()

        cursor = conn.cursor()


        try:

            cursor.execute(
                """
                SELECT
                    ActiveSessionToken,
                    IsActive

                FROM Users

                WHERE UserID = ?

                  AND Role =
                      'Shipper'
                """,
                (
                    session.get(
                        "user_id"
                    ),
                ),
            )


            user = (
                cursor.fetchone()
            )


            if (
                not user
                or
                user.IsActive != 1
                or
                not user.ActiveSessionToken
                or
                user.ActiveSessionToken
                !=
                token
            ):

                session.clear()


                return jsonify({

                    "logged_in":
                        False,

                    "reason":
                        "SESSION_CONFLICT",

                })


        finally:

            cursor.close()

            conn.close()


    return jsonify({

        "logged_in":
            True,

        "user_id":
            session.get(
                "user_id"
            ),

        "username":
            session.get(
                "username"
            ),

        "fullname":
            session.get(
                "fullname"
            ),

        "role":
            session.get(
                "role"
            ),

    })

@app.route(
    "/logout"
)
def logout():
    """Đăng xuất an toàn với Single Active Shipper Session."""

    user_id = (
        session.get(
            "user_id"
        )
    )


    role = (
        session.get(
            "role"
        )
    )


    token = (
        session.get(
            "shipper_session_token"
        )
    )


    # =====================================================
    # CHỈ XÓA TOKEN NẾU TOKEN DB VẪN LÀ TOKEN CỦA MÁY NÀY
    # =====================================================

    if (
        role == "Shipper"
        and
        user_id
        and
        token
    ):

        conn = get_connection()

        cursor = conn.cursor()


        try:

            cursor.execute(
                """
                UPDATE Users

                SET
                    ActiveSessionToken =
                        NULL,

                    SessionUpdatedAt =
                        SYSDATETIME()

                WHERE UserID = ?

                  AND Role =
                      'Shipper'

                  AND ActiveSessionToken = ?
                """,
                (
                    user_id,
                    token,
                ),
            )


            conn.commit()


        finally:

            cursor.close()

            conn.close()


    session.clear()


    return redirect(
        url_for(
            "login"
        )
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


@app.route(
    "/api/orders",
    methods=["POST"],
)
def create_order():
    """Tạo đơn hàng mới."""

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )


    # =====================================================
    # CUSTOMER
    # =====================================================

    customer_name = (
        data.get(
            "customerName"
        )
        or ""
    ).strip()


    phone = (
        data.get(
            "phone"
        )
        or ""
    ).strip()


    address = (
        data.get(
            "address"
        )
        or ""
    ).strip()


    note = (
        data.get(
            "note"
        )
        or ""
    ).strip()


    latitude = (
        data.get(
            "latitude"
        )
    )


    longitude = (
        data.get(
            "longitude"
        )
    )


    products = (
        data.get(
            "products"
        )
        or []
    )


    # =====================================================
    # PAYMENT
    # =====================================================

    payment_method = (
        data.get(
            "paymentMethod"
        )
        or ""
    ).strip().upper()


    allowed_payment_methods = {
        "CASH",
        "BANK_TRANSFER",
    }


    if (
        payment_method
        not in
        allowed_payment_methods
    ):

        return jsonify({

            "success":
                False,

            "message":
                "Phương thức thanh toán không hợp lệ.",

        }), 400


    if (
        payment_method
        ==
        "CASH"
    ):

        payment_status = (
            "Thanh toán khi nhận hàng"
        )

    else:

        payment_status = (
            "Chờ khách chuyển khoản"
        )


    # =====================================================
    # VALIDATE CUSTOMER
    # =====================================================

    if not customer_name:

        return jsonify({

            "success":
                False,

            "message":
                "Vui lòng nhập họ tên.",

        }), 400


    if not phone:

        return jsonify({

            "success":
                False,

            "message":
                "Vui lòng nhập số điện thoại.",

        }), 400


    if (
        not address
        or
        latitude in (
            None,
            "",
        )
        or
        longitude in (
            None,
            "",
        )
    ):

        return jsonify({

            "success":
                False,

            "message":
                "Vui lòng chọn vị trí giao hàng.",

        }), 400


    if (
        not isinstance(
            products,
            list
        )
        or
        len(
            products
        )
        ==
        0
    ):

        return jsonify({

            "success":
                False,

            "message":
                "Giỏ hàng đang trống.",

        }), 400


    # =====================================================
    # CALCULATE TOTAL
    # =====================================================

    try:

        total_money = sum(

            float(
                product["price"]
            )
            *
            int(
                product["quantity"]
            )

            for product
            in products

        )


        shipping_fee = float(
            data.get(
                "shippingFee"
            )
            or 0
        )


    except (
        TypeError,
        ValueError,
        KeyError,
    ):

        return jsonify({

            "success":
                False,

            "message":
                "Dữ liệu giỏ hàng không hợp lệ.",

        }), 400


    # =====================================================
    # ORDER CODE
    # =====================================================

    order_code = (

        "BCV"

        +

        str(
            int(
                time.time()
            )
        )[-6:]

    )


    conn = get_connection()

    cursor = conn.cursor()


    try:

        # =================================================
        # INSERT ORDER
        # =================================================

        cursor.execute(
            """
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

                Status,

                PaymentMethod,

                PaymentStatus
            )

            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?
            )
            """,
            (
                order_code,

                customer_name,

                phone,

                address,

                latitude,

                longitude,

                note,

                total_money,

                shipping_fee,

                "Đã tiếp nhận",

                payment_method,

                payment_status,
            ),
        )


        conn.commit()


        total_amount = (
            total_money
            +
            shipping_fee
        )


        return jsonify({

            "success":
                True,

            "orderCode":
                order_code,

            "paymentMethod":
                payment_method,

            "paymentStatus":
                payment_status,

            "totalAmount":
                total_amount,

        })


    except Exception as error:

        conn.rollback()


        print(
            "LỖI TẠO ĐƠN:",
            error
        )


        return jsonify({

            "success":
                False,

            "message":
                "Không thể tạo đơn hàng.",

        }), 500


    finally:

        cursor.close()

        conn.close()

@app.route(
    "/api/orders/<order_code>/payment-reported",
    methods=["POST"],
)
def report_bank_transfer(
    order_code: str,
):
    """
    Khách tự xác nhận đã thực hiện chuyển khoản.

    Lưu ý:
    API này KHÔNG xác minh tiền thực tế đã vào ngân hàng.
    """

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )


    phone = (
        data.get(
            "phone"
        )
        or ""
    ).strip()


    if not phone:

        return jsonify({

            "success":
                False,

            "message":
                "Thiếu số điện thoại xác minh đơn hàng.",

        }), 400


    conn = get_connection()

    cursor = conn.cursor()


    try:

        # =================================================
        # CHECK ORDER
        # =================================================

        cursor.execute(
            """
            SELECT
                OrderID,
                PaymentMethod,
                PaymentStatus

            FROM Orders

            WHERE OrderCode = ?

              AND Phone = ?
            """,
            (
                order_code,
                phone,
            ),
        )


        order = (
            cursor.fetchone()
        )


        if not order:

            return jsonify({

                "success":
                    False,

                "message":
                    "Không tìm thấy đơn hàng.",

            }), 404


        if (
            order.PaymentMethod
            !=
            "BANK_TRANSFER"
        ):

            return jsonify({

                "success":
                    False,

                "message":
                    "Đơn hàng này không sử dụng chuyển khoản.",

            }), 400


        # =================================================
        # UPDATE PAYMENT REPORT
        # =================================================

        cursor.execute(
            """
            UPDATE Orders

            SET
                PaymentStatus =
                    N'Khách báo đã chuyển khoản',

                PaymentReportedAt =
                    GETDATE()

            WHERE OrderID = ?
            """,
            (
                order.OrderID,
            ),
        )


        conn.commit()


        return jsonify({

            "success":
                True,

            "paymentStatus":
                "Khách báo đã chuyển khoản",

            "message":
                "Đã ghi nhận thông báo chuyển khoản.",

        })


    except Exception as error:

        conn.rollback()


        print(
            "LỖI PAYMENT REPORT:",
            error
        )


        return jsonify({

            "success":
                False,

            "message":
                "Không thể cập nhật trạng thái thanh toán.",

        }), 500


    finally:

        cursor.close()

        conn.close()
@app.route("/api/orders/<phone>")
def get_orders(phone):
    """Tra cứu các đơn hàng theo số điện thoại của khách."""

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
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
                (
                    CONVERT(VARCHAR(10), o.CreatedAt, 103)
                    + ' '
                    + LEFT(CONVERT(VARCHAR(8), o.CreatedAt, 108), 5)
                ) AS CreatedTime,
                o.DriverID,
                u.FullName AS DriverName
            FROM Orders o
            LEFT JOIN Users u
                ON o.DriverID = u.UserID
            WHERE o.Phone = ?
            ORDER BY o.OrderID DESC
            """,
            (phone,),
        )

        orders = cursor.fetchall()
        result = []

        for order in orders:
            food_total = Decimal(order.TotalMoney or 0)
            shipping_fee = Decimal(order.ShippingFee or 0)

            result.append({
                "id": order.OrderID,
                "code": order.OrderCode,
                "name": order.CustomerName,
                "address": order.Address,
                "foodTotal": float(food_total),
                "shippingFee": float(shipping_fee),
                "total": float(food_total + shipping_fee),
                "status": order.Status,
                "createdAt": order.CreatedTime or "",
                # Đây là tọa độ ĐÍCH GIAO HÀNG của khách.
                # Không được dùng hai trường này làm GPS shipper.
                "latitude": (
                    float(order.Latitude)
                    if order.Latitude is not None
                    else None
                ),
                "longitude": (
                    float(order.Longitude)
                    if order.Longitude is not None
                    else None
                ),
                "driverId": order.DriverID,
                "driverName": order.DriverName,
            })

        return jsonify(result)

    except Exception as error:
        print("LỖI TRA CỨU ĐƠN:", error)
        return jsonify({
            "success": False,
            "message": "Không thể tra cứu đơn hàng.",
        }), 500

    finally:
        cursor.close()
        conn.close()


@app.route("/api/orders/<order_code>/tracking")
def get_order_tracking(order_code):
    """Trả vị trí GPS mới nhất của shipper cho một đơn đang giao.

    Orders.Latitude/Longitude là tọa độ khách hàng.
    DriverLocations.Latitude/Longitude mới là tọa độ shipper.
    """

    phone = (request.args.get("phone") or "").strip()

    if not phone:
        return jsonify({
            "success": False,
            "message": "Thiếu số điện thoại xác minh đơn hàng.",
        }), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT
                o.OrderID,
                o.OrderCode,
                o.Status,
                o.DriverID,
                o.Latitude AS CustomerLatitude,
                o.Longitude AS CustomerLongitude,
                u.FullName AS DriverName
            FROM Orders o
            LEFT JOIN Users u
                ON o.DriverID = u.UserID
            WHERE o.OrderCode = ?
              AND o.Phone = ?
            """,
            (order_code, phone),
        )

        order = cursor.fetchone()

        if not order:
            return jsonify({
                "success": False,
                "message": "Không tìm thấy đơn hàng.",
            }), 404

        response = {
            "success": True,
            "orderCode": order.OrderCode,
            "status": order.Status,
            "destination": {
                "latitude": (
                    float(order.CustomerLatitude)
                    if order.CustomerLatitude is not None
                    else None
                ),
                "longitude": (
                    float(order.CustomerLongitude)
                    if order.CustomerLongitude is not None
                    else None
                ),
            },
            "driver": None,
        }

        if not order.DriverID:
            response["message"] = "Đơn chưa được phân công shipper."
            return jsonify(response)

        cursor.execute(
            """
            SELECT TOP 1
                Latitude,
                Longitude,
                (
                    CONVERT(VARCHAR(10), UpdatedAt, 103)
                    + ' '
                    + LEFT(CONVERT(VARCHAR(8), UpdatedAt, 108), 5)
                ) AS UpdatedTime,
                DATEDIFF(SECOND, UpdatedAt, GETDATE()) AS AgeSeconds
            FROM DriverLocations
            WHERE DriverID = ?
            ORDER BY UpdatedAt DESC, LocationID DESC
            """,
            (order.DriverID,),
        )

        location = cursor.fetchone()

        if not location:
            response["message"] = "Shipper chưa gửi vị trí GPS."
            return jsonify(response)

        age_seconds = max(int(location.AgeSeconds or 0), 0)

        response["driver"] = {
            "id": order.DriverID,
            "name": order.DriverName or "Shipper",
            "latitude": float(location.Latitude),
            "longitude": float(location.Longitude),
            "updatedAt": location.UpdatedTime or "",
            "ageSeconds": age_seconds,
            "isFresh": age_seconds <= 30,
        }

        return jsonify(response)

    except Exception as error:
        print("LỖI TRACKING SHIPPER:", error)
        return jsonify({
            "success": False,
            "message": "Không thể lấy vị trí shipper.",
        }), 500

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

# ============================================================
# CONTACT PAGE
# ============================================================

@app.route(
    "/contact"
)
def contact_page() -> str:
    """Hiển thị trang liên hệ."""

    return render_template(
        "contact.html"
    )


# ============================================================
# CREATE CONTACT
# ============================================================

@app.route(
    "/api/contact",
    methods=["POST"],
)
def create_contact():
    """Tiếp nhận yêu cầu liên hệ từ khách hàng."""

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )


    # ========================================================
    # INPUT
    # ========================================================

    full_name = (
        data.get(
            "fullName"
        )
        or ""
    ).strip()


    phone = (
        data.get(
            "phone"
        )
        or ""
    ).strip()


    email = (
        data.get(
            "email"
        )
        or ""
    ).strip()


    subject = (
        data.get(
            "subject"
        )
        or ""
    ).strip()


    order_code = (
        data.get(
            "orderCode"
        )
        or ""
    ).strip().upper()


    message = (
        data.get(
            "message"
        )
        or ""
    ).strip()


    # ========================================================
    # VALID SUBJECTS
    # ========================================================

    allowed_subjects = {

        "Góp ý món ăn",

        "Phản ánh đơn hàng",

        "Hỗ trợ giao hàng",

        "Thanh toán",

        "Hợp tác",

        "Khác",

    }


    # ========================================================
    # VALIDATE
    # ========================================================

    if not full_name:

        return jsonify({

            "success":
                False,

            "message":
                "Vui lòng nhập họ và tên.",

        }), 400


    if len(full_name) > 100:

        return jsonify({

            "success":
                False,

            "message":
                "Họ tên quá dài.",

        }), 400


    if not phone:

        return jsonify({

            "success":
                False,

            "message":
                "Vui lòng nhập số điện thoại.",

        }), 400


    normalized_phone = (
        phone
        .replace(" ", "")
        .replace("-", "")
    )


    if (
        not normalized_phone.isdigit()
        or
        len(normalized_phone) < 9
        or
        len(normalized_phone) > 12
    ):

        return jsonify({

            "success":
                False,

            "message":
                "Số điện thoại không hợp lệ.",

        }), 400


    if (
        subject
        not in
        allowed_subjects
    ):

        return jsonify({

            "success":
                False,

            "message":
                "Chủ đề liên hệ không hợp lệ.",

        }), 400


    if not message:

        return jsonify({

            "success":
                False,

            "message":
                "Vui lòng nhập nội dung liên hệ.",

        }), 400


    if len(message) > 1000:

        return jsonify({

            "success":
                False,

            "message":
                "Nội dung liên hệ tối đa 1000 ký tự.",

        }), 400


    # ========================================================
    # ORDER COMPLAINT REQUIRES ORDER CODE
    # ========================================================

    if (
        subject
        ==
        "Phản ánh đơn hàng"
        and
        not order_code
    ):

        return jsonify({

            "success":
                False,

            "message":
                "Vui lòng nhập mã đơn hàng cần phản ánh.",

        }), 400


    conn = get_connection()

    cursor = conn.cursor()


    try:

        # ====================================================
        # VERIFY ORDER WHEN ORDER CODE PROVIDED
        # ====================================================

        if order_code:

            cursor.execute(
                """
                SELECT
                    OrderID

                FROM Orders

                WHERE OrderCode = ?

                  AND Phone = ?
                """,
                (
                    order_code,
                    phone,
                ),
            )


            order = (
                cursor.fetchone()
            )


            if not order:

                return jsonify({

                    "success":
                        False,

                    "message":
                        "Không tìm thấy đơn hàng khớp với "
                        "mã đơn và số điện thoại đã nhập.",

                }), 400


        # ====================================================
        # INSERT CONTACT
        # ====================================================

        cursor.execute(
            """
            INSERT INTO Contacts
            (
                FullName,
                Phone,
                Email,
                Subject,
                OrderCode,
                Message,
                Status,
                CreatedAt
            )

            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                N'Mới',
                SYSDATETIME()
            )
            """,
            (
                full_name,
                phone,
                email or None,
                subject,
                order_code or None,
                message,
            ),
        )


        conn.commit()


        return jsonify({

            "success":
                True,

            "message":
                "Bún Chả Việt đã nhận được lời nhắn của bạn.",

        })


    except Exception as error:

        conn.rollback()


        print(
            "LỖI CONTACT:",
            error
        )


        return jsonify({

            "success":
                False,

            "message":
                "Không thể gửi liên hệ lúc này.",

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
