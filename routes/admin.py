from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    request,
    jsonify
)

from database import get_connection

from werkzeug.utils import secure_filename

import os


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)


UPLOAD_FOLDER = "static/images"




# =========================================================
# CHECK ADMIN
# =========================================================

def check_admin():

    return session.get("role") == "Admin"




# =========================================================
# DASHBOARD
# =========================================================

@admin_bp.route("/dashboard")
def dashboard():

    if not check_admin():
        return redirect(url_for("login"))


    return render_template(
        "admin/dashboard.html",
        username=session.get("fullname")
    )




# =========================================================
# PRODUCT LIST
# =========================================================

@admin_bp.route("/products")
def products():

    if not check_admin():
        return redirect(url_for("login"))


    conn = get_connection()

    cursor = conn.cursor()



    cursor.execute("""
        SELECT
            p.ProductID,
            p.ProductName,
            p.Description,
            p.Price,
            p.Image,
            p.CategoryID,
            c.CategoryName

        FROM Products p

        LEFT JOIN Categories c
        ON p.CategoryID = c.CategoryID

        WHERE p.IsActive = 1

        ORDER BY p.ProductID DESC
    """)


    products = cursor.fetchall()



    cursor.execute("""
        SELECT
            CategoryID,
            CategoryName

        FROM Categories
    """)


    categories = cursor.fetchall()



    cursor.close()

    conn.close()



    return render_template(
        "admin/products.html",
        products=products,
        categories=categories
    )




# =========================================================
# ADD PRODUCT
# =========================================================

@admin_bp.route(
    "/products/add",
    methods=["POST"]
)
def add_product():

    if not check_admin():

        return jsonify({
            "success": False
        })



    name = request.form.get("name")

    description = request.form.get("description")

    price = request.form.get("price")

    category = request.form.get("category")



    image = request.files.get("image")

    filename = ""



    if image and image.filename:


        filename = secure_filename(
            image.filename
        )


        os.makedirs(
            UPLOAD_FOLDER,
            exist_ok=True
        )


        image.save(
            os.path.join(
                UPLOAD_FOLDER,
                filename
            )
        )




    conn = get_connection()

    cursor = conn.cursor()



    cursor.execute("""
        INSERT INTO Products
        (
            ProductName,
            Description,
            Price,
            Image,
            CategoryID,
            IsActive
        )

        VALUES
        (?, ?, ?, ?, ?, 1)

    """,
    (
        name,
        description,
        price,
        filename,
        category
    ))



    conn.commit()

    cursor.close()

    conn.close()



    return jsonify({
        "success": True
    })






# =========================================================
# UPDATE PRODUCT
# =========================================================

@admin_bp.route(
    "/products/edit/<int:id>",
    methods=["POST"]
)
def update_product(id):

    if not check_admin():

        return jsonify({
            "success": False
        })



    name = request.form.get("name")

    description = request.form.get("description")

    price = request.form.get("price")

    category = request.form.get("category")



    image = request.files.get("image")



    conn = get_connection()

    cursor = conn.cursor()



    # Có upload ảnh mới

    if image and image.filename:


        filename = secure_filename(
            image.filename
        )


        os.makedirs(
            UPLOAD_FOLDER,
            exist_ok=True
        )


        image.save(
            os.path.join(
                UPLOAD_FOLDER,
                filename
            )
        )



        cursor.execute("""
            UPDATE Products

            SET
                ProductName=?,
                Description=?,
                Price=?,
                CategoryID=?,
                Image=?

            WHERE ProductID=?

        """,
        (
            name,
            description,
            price,
            category,
            filename,
            id
        ))


    else:


        cursor.execute("""
            UPDATE Products

            SET
                ProductName=?,
                Description=?,
                Price=?,
                CategoryID=?

            WHERE ProductID=?

        """,
        (
            name,
            description,
            price,
            category,
            id
        ))





    conn.commit()

    cursor.close()

    conn.close()



    return jsonify({
        "success": True
    })



# =========================================================
# DELETE PRODUCT
# =========================================================

@admin_bp.route(
    "/products/delete/<int:id>",
    methods=["DELETE"]
)
def delete_product(id):

    if not check_admin():

        return jsonify({
            "success": False
        })



    conn = get_connection()

    cursor = conn.cursor()



    cursor.execute("""
        UPDATE Products

        SET IsActive = 0

        WHERE ProductID = ?

    """,
    (id,))



    conn.commit()

    cursor.close()

    conn.close()



    return jsonify({
        "success": True
    })



# =========================================================
# OTHER ADMIN PAGE
# =========================================================


@admin_bp.route("/users")
def users():

    if not check_admin():
        return redirect(url_for("login"))


    return render_template(
        "admin/users.html"
    )


@admin_bp.route("/categories")
def categories():

    if not check_admin():
        return redirect(url_for("login"))


    return render_template(
        "admin/categories.html"
    )
@admin_bp.route("/orders")
def orders():
    if not check_admin():
        return redirect(url_for("login"))

    date = request.args.get("date", "").strip()
    month = request.args.get("month", "").strip()
    status = request.args.get("status", "").strip()

    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT *
        FROM Orders
        WHERE 1 = 1
    """

    params = []

    if date:
        query += " AND CAST(CreatedAt AS DATE) = ?"
        params.append(date)

    elif month:
        year, month_number = month.split("-")

        query += """
            AND YEAR(CreatedAt) = ?
            AND MONTH(CreatedAt) = ?
        """

        params.extend([
            int(year),
            int(month_number)
        ])

    if status:
        query += " AND Status = ?"
        params.append(status)

    query += " ORDER BY CreatedAt DESC"

    cursor.execute(query, params)
    orders = cursor.fetchall()

    cursor.execute("""
        SELECT UserID, FullName
        FROM Users
        WHERE Role = 'Shipper'
          AND IsActive = 1
        ORDER BY FullName
    """)

    shippers = cursor.fetchall()

    cursor.close()
    conn.close()

    # ================================
    # GROUP ĐƠN THEO NGÀY
    # ================================

    grouped_orders = {}

    for order in orders:
        order_date = order.CreatedAt.date()

        if order_date not in grouped_orders:
            grouped_orders[order_date] = []

        grouped_orders[order_date].append(order)

    return render_template(
        "admin/orders.html",
        orders=orders,
        grouped_orders=grouped_orders,
        shippers=shippers,
        selected_date=date,
        selected_month=month,
        selected_status=status
    )

@admin_bp.route(
"/orders/assign",
methods=["POST"]
)
def assign_shipper():


    if not check_admin():

        return jsonify({
            "success":False
        })



    data=request.json



    order_id=data.get("orderId")

    driver_id=data.get("driverId")



    conn=get_connection()

    cursor=conn.cursor()



    cursor.execute("""
        UPDATE Orders

        SET
        DriverID=?,
        Status='Đã giao shipper'

        WHERE OrderID=?

    """,
    (
        driver_id,
        order_id
    ))



    conn.commit()


    cursor.close()

    conn.close()



    return jsonify({

        "success":True

    })

# =========================================================
# QUẢN LÝ SHIPPER
# =========================================================

@admin_bp.route("/shippers")
def shippers():
    if not check_admin():
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            u.UserID,
            u.Username,
            u.FullName,
            u.Phone,
            u.IsActive,
            COUNT(o.OrderID) AS ActiveOrders
        FROM Users u
        LEFT JOIN Orders o
            ON o.DriverID = u.UserID
            AND o.Status = 'Đang giao'
        WHERE u.Role = 'Shipper'
        GROUP BY
            u.UserID,
            u.Username,
            u.FullName,
            u.Phone,
            u.IsActive
        ORDER BY u.UserID DESC
    """)

    shippers = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin/shippers.html",
        shippers=shippers
    )


# =========================================================
# THÊM SHIPPER
# =========================================================

@admin_bp.route("/shippers/add", methods=["POST"])
def add_shipper():
    if not check_admin():
        return jsonify({
            "success": False,
            "message": "Không có quyền!"
        }), 403

    data = request.get_json()

    fullname = data.get("fullname", "").strip()
    username = data.get("username", "").strip()
    password = data.get("password", "")
    phone = data.get("phone", "").strip()

    if not fullname or not username or not password:
        return jsonify({
            "success": False,
            "message": "Vui lòng nhập đầy đủ thông tin!"
        }), 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT UserID
        FROM Users
        WHERE Username = ?
    """, (username,))

    if cursor.fetchone():
        cursor.close()
        conn.close()

        return jsonify({
            "success": False,
            "message": "Tên đăng nhập đã tồn tại!"
        }), 400

    cursor.execute("""
        INSERT INTO Users
        (
            Username,
            Password,
            FullName,
            Phone,
            Role,
            IsActive
        )
        VALUES (?, ?, ?, ?, 'Shipper', 1)
    """, (
        username,
        password,
        fullname,
        phone
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({
        "success": True
    })


# =========================================================
# SỬA SHIPPER
# =========================================================

@admin_bp.route("/shippers/update/<int:id>", methods=["POST"])
def update_shipper(id):
    if not check_admin():
        return jsonify({
            "success": False,
            "message": "Không có quyền!"
        }), 403

    data = request.get_json()

    fullname = data.get("fullname", "").strip()
    username = data.get("username", "").strip()
    password = data.get("password", "")
    phone = data.get("phone", "").strip()

    conn = get_connection()
    cursor = conn.cursor()

    if password:
        cursor.execute("""
            UPDATE Users
            SET
                Username = ?,
                Password = ?,
                FullName = ?,
                Phone = ?
            WHERE UserID = ?
              AND Role = 'Shipper'
        """, (
            username,
            password,
            fullname,
            phone,
            id
        ))
    else:
        cursor.execute("""
            UPDATE Users
            SET
                Username = ?,
                FullName = ?,
                Phone = ?
            WHERE UserID = ?
              AND Role = 'Shipper'
        """, (
            username,
            fullname,
            phone,
            id
        ))

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({
        "success": True
    })


# =========================================================
# KHÓA / MỞ KHÓA SHIPPER
# =========================================================

@admin_bp.route("/shippers/status/<int:id>", methods=["POST"])
def update_shipper_status(id):
    if not check_admin():
        return jsonify({
            "success": False,
            "message": "Không có quyền!"
        }), 403

    data = request.get_json()

    is_active = data.get("isActive")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE Users
        SET IsActive = ?
        WHERE UserID = ?
          AND Role = 'Shipper'
    """, (
        is_active,
        id
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({
        "success": True
    })