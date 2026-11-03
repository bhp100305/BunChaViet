
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
from datetime import timedelta
import os
import time
import secrets
import json
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request as URLRequest, urlopen
from routes.product import product_bp
from database import get_connection
from routes.admin import admin_bp
from routes.admin_orders import admin_orders_bp
from routes.admin_products import admin_products_bp
from routes.admin_shippers import admin_shippers_bp
from routes.shipper import shipper_bp
from routes.admin_contacts import admin_contacts_bp
from routes.email_otp import email_otp_bp
from routes.customer_auth import customer_auth_bp
app = Flask(__name__)

def get_flask_secret_key() -> str:
    """Dùng khóa cấu hình; nếu thiếu thì tạo một khóa ổn định trên máy chạy app."""
    configured_key = os.getenv("FLASK_SECRET_KEY")
    if configured_key:
        return configured_key

    key_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        ".flask_secret_key",
    )

    try:
        with open(key_path, "r", encoding="ascii") as key_file:
            return key_file.read().strip()
    except FileNotFoundError:
        generated_key = secrets.token_urlsafe(48)
        try:
            with open(key_path, "x", encoding="ascii") as key_file:
                key_file.write(generated_key)
            return generated_key
        except FileExistsError:
            with open(key_path, "r", encoding="ascii") as key_file:
                return key_file.read().strip()


app.secret_key = get_flask_secret_key()
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
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
app.register_blueprint(admin_orders_bp)
app.register_blueprint(admin_products_bp)
app.register_blueprint(admin_shippers_bp)
app.register_blueprint(shipper_bp)
app.register_blueprint(admin_contacts_bp)
app.register_blueprint(email_otp_bp)
app.register_blueprint(customer_auth_bp)
@app.route("/")
def home():

    return render_template(
        "index.html",
        customer_logged_in=bool(session.get("customer_id")),
    )


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

        session.permanent = True


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

    if not session.get("customer_id"):
        return redirect("/customer/login")

    return render_template(
        "checkout.html"
    )


@app.route("/api/geocode/reverse")
def reverse_geocode_address():
    """Tra địa chỉ từ tọa độ giao hàng qua Nominatim."""
    try:
        latitude = float(request.args.get("lat", ""))
        longitude = float(request.args.get("lon", ""))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Tọa độ không hợp lệ."}), 400

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return jsonify({"success": False, "message": "Tọa độ nằm ngoài phạm vi hợp lệ."}), 400

    query = urlencode({
        "format": "jsonv2",
        "lat": latitude,
        "lon": longitude,
        "accept-language": "vi",
    })
    upstream = URLRequest(
        f"https://nominatim.openstreetmap.org/reverse?{query}",
        headers={
            "User-Agent": "NguonMoDelivery/1.0",
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(upstream, timeout=8) as response:
            result = json.loads(response.read().decode("utf-8"))
        address = (result.get("display_name") or "").strip()
        if not address:
            return jsonify({"success": False, "message": "Không tìm thấy địa chỉ cho vị trí này."}), 404
        return jsonify({"success": True, "address": address})
    except (URLError, TimeoutError, ValueError) as error:
        app.logger.warning("Reverse geocoding failed: %s", error)
        return jsonify({"success": False, "message": "Dịch vụ tìm địa chỉ hiện không phản hồi."}), 502


@app.route("/api/geocode/search")
def search_geocode_address():
    """Tìm gợi ý địa chỉ giao hàng qua Nominatim, tránh CORS trên mobile."""
    keyword = (request.args.get("q") or "").strip()
    if len(keyword) < 3:
        return jsonify({"success": False, "message": "Nhập ít nhất 3 ký tự để tìm địa chỉ."}), 400

    query = urlencode({
        "format": "jsonv2",
        "limit": 5,
        "countrycodes": "vn",
        "accept-language": "vi",
        "q": keyword,
    })
    upstream = URLRequest(
        f"https://nominatim.openstreetmap.org/search?{query}",
        headers={
            "User-Agent": "NguonMoDelivery/1.0",
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(upstream, timeout=8) as response:
            places = json.loads(response.read().decode("utf-8"))
        results = [
            {
                "display_name": (place.get("display_name") or "").strip(),
                "lat": place.get("lat"),
                "lon": place.get("lon"),
            }
            for place in places
            if place.get("display_name") and place.get("lat") and place.get("lon")
        ]
        return jsonify({"success": True, "results": results})
    except (URLError, TimeoutError, ValueError) as error:
        app.logger.warning("Address search failed: %s", error)
        return jsonify({"success": False, "message": "Dịch vụ tìm địa chỉ hiện không phản hồi."}), 502

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

    if not session.get("customer_id"):
        return jsonify({"success": False, "message": "Vui lòng đăng nhập trước khi đặt hàng.", "redirect": "/customer/login"}), 401

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

    try:
        product_ids = []
        for item in products:
            if not isinstance(item, dict):
                raise ValueError("Invalid product")
            product_ids.append(int(item.get("id") or item.get("productId")))
        if any(product_id <= 0 for product_id in product_ids):
            raise ValueError("Invalid product")
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "Giỏ hàng có món không hợp lệ. Vui lòng tải lại thực đơn.",
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

        placeholders = ",".join("?" for _ in product_ids)
        cursor.execute(
            f"""
            SELECT ProductID, IsActive, IsAvailable
            FROM Products
            WHERE ProductID IN ({placeholders})
            """,
            product_ids,
        )
        current_products = {
            int(row.ProductID): row
            for row in cursor.fetchall()
        }
        if any(product_id not in current_products or not current_products[product_id].IsActive
               for product_id in product_ids):
            conn.rollback()
            return jsonify({
                "success": False,
                "message": "Một món trong giỏ đã được lưu trữ. Vui lòng tải lại thực đơn.",
            }), 409
        if any(not current_products[product_id].IsAvailable for product_id in product_ids):
            conn.rollback()
            return jsonify({
                "success": False,
                "message": "Một món trong giỏ vừa hết hàng. Vui lòng cập nhật giỏ hàng.",
            }), 409

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
