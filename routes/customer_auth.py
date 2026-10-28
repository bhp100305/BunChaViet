from __future__ import annotations

import hashlib
import hmac
import secrets
import time

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session

from database import get_connection

customer_auth_bp = Blueprint("customer_auth", __name__)
PASSWORD_ITERATIONS = 310_000
OTP_VALID_SECONDS = 15 * 60


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def verified_registration_email() -> str:
    email = str(session.get("checkout_verified_email") or "").strip().lower()
    verified_at = int(session.get("checkout_verified_email_at") or 0)
    if not email or not verified_at or time.time() - verified_at > OTP_VALID_SECONDS:
        return ""
    return email


@customer_auth_bp.get("/customer/register")
def register_page():
    if session.get("customer_id"):
        return redirect("/")
    return render_template("customer_register.html")


@customer_auth_bp.get("/customer/login")
def login_page():
    if session.get("customer_id"):
        return redirect("/")
    return render_template("customer_login.html")


@customer_auth_bp.get("/customer/profile")
def customer_profile_page():
    if not session.get("customer_id"):
        return redirect("/customer/login")
    return render_template("customer_profile.html")


@customer_auth_bp.post("/api/customer/register")
def register_customer():
    data = request.get_json(silent=True) or {}
    full_name = str(data.get("fullName") or "").strip()
    phone = str(data.get("phone") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")
    if not full_name or len(full_name) > 100 or not phone or len(phone) > 20:
        return jsonify(success=False, message="Vui lòng nhập họ tên và số điện thoại hợp lệ."), 400
    if len(email) > 255 or "@" not in email:
        return jsonify(success=False, message="Email không hợp lệ."), 400
    if len(password) < 8 or len(password) > 128:
        return jsonify(success=False, message="Mật khẩu cần có từ 8 đến 128 ký tự."), 400
    if verified_registration_email() != email:
        return jsonify(success=False, message="Hãy xác thực đúng email bằng mã OTP trước khi đăng ký."), 403

    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT CustomerID FROM Customers WHERE Email = ?", email)
        if cursor.fetchone():
            return jsonify(success=False, message="Email này đã được đăng ký."), 409
        cursor.execute(
            "INSERT INTO Customers (FullName, Email, Phone, PasswordHash, IsActive, CreatedAt) VALUES (?, ?, ?, ?, 1, SYSDATETIME())",
            full_name, email, phone, hash_password(password),
        )
        conn.commit()
        session.pop("checkout_verified_email", None)
        session.pop("checkout_verified_email_at", None)
        return jsonify(success=True, message="Tạo tài khoản thành công.", redirect="/customer/login"), 201
    except Exception:
        if conn:
            conn.rollback()
        return jsonify(success=False, message="Chưa thể tạo tài khoản. Vui lòng thử lại."), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@customer_auth_bp.post("/api/customer/login")
def login_customer():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT CustomerID, FullName, Email, PasswordHash FROM Customers WHERE Email = ? AND IsActive = 1", email)
        customer = cursor.fetchone()
        if not customer or not verify_password(password, str(customer.PasswordHash)):
            return jsonify(success=False, message="Email hoặc mật khẩu không đúng."), 401
        session.clear()
        session["customer_id"] = int(customer.CustomerID)
        session["customer_email"] = str(customer.Email)
        session["customer_name"] = str(customer.FullName)
        return jsonify(success=True, customer={"id": int(customer.CustomerID), "email": str(customer.Email), "name": str(customer.FullName)}, redirect="/")
    except Exception:
        return jsonify(success=False, message="Chưa thể đăng nhập. Vui lòng thử lại."), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@customer_auth_bp.post("/api/customer/logout")
def logout_customer():
    session.pop("customer_id", None)
    session.pop("customer_email", None)
    session.pop("customer_name", None)
    return jsonify(success=True, redirect="/")


@customer_auth_bp.get("/api/customer/session")
def customer_session():
    customer_id = session.get("customer_id")
    if not customer_id:
        return jsonify(authenticated=False)
    return jsonify(authenticated=True, customer={"id": customer_id, "email": session.get("customer_email"), "name": session.get("customer_name")})


@customer_auth_bp.get("/api/customer/profile")
def get_customer_profile():
    customer_id = session.get("customer_id")
    if not customer_id:
        return jsonify(success=False, message="Vui lòng đăng nhập để xem hồ sơ."), 401
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT FullName, Email, Phone FROM Customers WHERE CustomerID = ? AND IsActive = 1",
            customer_id,
        )
        customer = cursor.fetchone()
        if not customer:
            session.clear()
            return jsonify(success=False, message="Tài khoản không còn hoạt động."), 401
        return jsonify(success=True, profile={
            "fullName": str(customer.FullName),
            "email": str(customer.Email),
            "phone": str(customer.Phone),
        })
    except Exception:
        current_app.logger.exception("Could not load customer profile for customer_id=%s", customer_id)
        return jsonify(success=False, message="Chưa thể tải hồ sơ. Vui lòng thử lại."), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@customer_auth_bp.put("/api/customer/profile")
def update_customer_profile():
    customer_id = session.get("customer_id")
    if not customer_id:
        return jsonify(success=False, message="Vui lòng đăng nhập để cập nhật hồ sơ."), 401
    data = request.get_json(silent=True) or {}
    full_name = str(data.get("fullName") or "").strip()
    phone = str(data.get("phone") or "").strip()
    if not full_name or len(full_name) > 100:
        return jsonify(success=False, message="Họ tên cần có từ 1 đến 100 ký tự."), 400
    if not phone or len(phone) > 20:
        return jsonify(success=False, message="Số điện thoại không hợp lệ."), 400
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE Customers SET FullName = ?, Phone = ? WHERE CustomerID = ? AND IsActive = 1",
            full_name, phone, customer_id,
        )
        if cursor.rowcount != 1:
            conn.rollback()
            return jsonify(success=False, message="Không tìm thấy tài khoản đang hoạt động."), 404
        conn.commit()
        session["customer_name"] = full_name
        return jsonify(success=True, message="Thông tin hồ sơ đã được cập nhật.", profile={"fullName": full_name, "phone": phone})
    except Exception:
        if conn:
            conn.rollback()
        return jsonify(success=False, message="Chưa thể cập nhật hồ sơ. Vui lòng thử lại."), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@customer_auth_bp.post("/api/customer/password")
def update_customer_password():
    customer_id = session.get("customer_id")
    if not customer_id:
        return jsonify(success=False, message="Vui lòng đăng nhập để đổi mật khẩu."), 401
    data = request.get_json(silent=True) or {}
    current_password = str(data.get("currentPassword") or "")
    new_password = str(data.get("newPassword") or "")
    if not current_password:
        return jsonify(success=False, message="Vui lòng nhập mật khẩu hiện tại."), 400
    if len(new_password) < 8 or len(new_password) > 128:
        return jsonify(success=False, message="Mật khẩu mới cần có từ 8 đến 128 ký tự."), 400
    conn = cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT PasswordHash FROM Customers WHERE CustomerID = ? AND IsActive = 1",
            customer_id,
        )
        row = cursor.fetchone()
        if not row or not verify_password(current_password, str(row.PasswordHash)):
            return jsonify(success=False, message="Mật khẩu hiện tại không đúng."), 400
        cursor.execute(
            "UPDATE Customers SET PasswordHash = ? WHERE CustomerID = ? AND IsActive = 1",
            hash_password(new_password), customer_id,
        )
        conn.commit()
        return jsonify(success=True, message="Mật khẩu đã được thay đổi.")
    except Exception:
        if conn:
            conn.rollback()
        return jsonify(success=False, message="Chưa thể đổi mật khẩu. Vui lòng thử lại."), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
