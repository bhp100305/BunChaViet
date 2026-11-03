from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import time
from collections import defaultdict, deque
from email.message import EmailMessage
from pathlib import Path
from threading import Lock

from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    request,
    session,
)

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# =========================================================
# BLUEPRINT
# =========================================================

email_otp_bp = Blueprint(
    "email_otp",
    __name__,
)


# =========================================================
# CONFIG
# =========================================================

# OTP tồn tại 5 phút
OTP_EXPIRES_SECONDS = 5 * 60

# Phải chờ 60 giây mới gửi lại OTP
OTP_RESEND_SECONDS = 60

# Tối đa nhập sai 5 lần
OTP_MAX_ATTEMPTS = 5

# Sau khi xác thực thành công,
# quyền đặt hàng tồn tại 15 phút
OTP_VERIFY_SESSION_SECONDS = 15 * 60

# Khoảng thời gian kiểm tra rate limit
RATE_WINDOW_SECONDS = 10 * 60

# Tối đa 3 OTP / email / 10 phút
MAX_SENDS_PER_EMAIL = 3

# Tối đa 10 OTP / IP / 10 phút
MAX_SENDS_PER_IP = 10


# =========================================================
# GMAIL API
# =========================================================

GMAIL_SCOPE = (
    "https://www.googleapis.com/auth/gmail.send"
)

SCOPES = [
    GMAIL_SCOPE
]


# Nếu không khai báo GMAIL_TOKEN_PATH
# thì dùng đường dẫn mặc định này
DEFAULT_GMAIL_TOKEN_PATH = Path(
    r"C:\BunChaVietSecrets\gmail_token.json"
)


# =========================================================
# RATE LIMIT MEMORY
# =========================================================

_rate_lock = Lock()

_email_send_log: dict[
    str,
    deque[float],
] = defaultdict(
    deque
)

_ip_send_log: dict[
    str,
    deque[float],
] = defaultdict(
    deque
)


# =========================================================
# EMAIL REGEX
# =========================================================

_EMAIL_RE = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+"
    r"@[A-Za-z0-9]"
    r"(?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9]"
    r"(?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)


# =========================================================
# NORMALIZE EMAIL
# =========================================================

def normalize_email(
    raw_email: str,
) -> str:
    """
    Chuẩn hóa và kiểm tra email.

    Args:
        raw_email:
            Email người dùng nhập.

    Returns:
        Email đã trim và lowercase.

    Raises:
        ValueError:
            Nếu email không hợp lệ.
    """

    email = (
        raw_email
        or ""
    ).strip().lower()

    if (
        not email
        or
        len(email) > 254
        or
        not _EMAIL_RE.fullmatch(
            email
        )
    ):
        raise ValueError(
            "Vui lòng nhập địa chỉ email hợp lệ."
        )

    return email


# =========================================================
# OTP SECRET
# =========================================================

def get_otp_secret() -> str:
    """
    Lấy secret server dùng để hash OTP.

    Ưu tiên:
    1. OTP_HMAC_SECRET
    2. FLASK_SECRET_KEY
    3. Flask secret_key hiện tại
    """

    secret = (
        os.getenv(
            "OTP_HMAC_SECRET"
        )
        or
        os.getenv(
            "FLASK_SECRET_KEY"
        )
        or
        str(
            current_app.secret_key
            or ""
        )
    )

    if not secret:
        raise RuntimeError(
            "Thiếu OTP_HMAC_SECRET "
            "hoặc FLASK_SECRET_KEY."
        )

    return secret


# =========================================================
# HASH OTP
# =========================================================

def hash_otp(
    email: str,
    otp_code: str,
) -> str:
    """
    Hash OTP.

    Không lưu OTP 6 số dạng plaintext
    vào Flask session.
    """

    payload = (
        f"{email}:{otp_code}"
    ).encode(
        "utf-8"
    )

    return hmac.new(
        get_otp_secret().encode(
            "utf-8"
        ),
        payload,
        hashlib.sha256,
    ).hexdigest()


# =========================================================
# CLIENT IP
# =========================================================

def get_client_ip() -> str:
    """
    Lấy IP thật của client.

    Hỗ trợ trường hợp Flask chạy
    phía sau ngrok/reverse proxy.
    """

    forwarded = (
        request.headers
        .get(
            "X-Forwarded-For"
        )
        or
        ""
    ).split(
        ","
    )[0].strip()

    return (
        forwarded
        or
        request.remote_addr
        or
        "unknown"
    )[:64]


# =========================================================
# RATE LIMIT
# =========================================================

def prune_log(
    log: deque[float],
    now: float,
) -> None:
    """
    Xóa các lần request cũ
    đã nằm ngoài rate-limit window.
    """

    cutoff = (
        now
        -
        RATE_WINDOW_SECONDS
    )

    while (
        log
        and
        log[0] < cutoff
    ):
        log.popleft()


def check_rate_limit(
    email: str,
    ip_address: str,
) -> tuple[
    bool,
    str,
]:
    """
    Chống spam gửi OTP.

    Returns:
        (True, "")
            nếu được gửi.

        (False, message)
            nếu vượt giới hạn.
    """

    now = time.time()

    with _rate_lock:

        email_log = (
            _email_send_log[
                email
            ]
        )

        ip_log = (
            _ip_send_log[
                ip_address
            ]
        )

        prune_log(
            email_log,
            now,
        )

        prune_log(
            ip_log,
            now,
        )

        if (
            len(email_log)
            >=
            MAX_SENDS_PER_EMAIL
        ):
            return (
                False,
                (
                    "Email này đã yêu cầu OTP "
                    "quá nhiều lần. "
                    "Vui lòng thử lại sau 10 phút."
                ),
            )

        if (
            len(ip_log)
            >=
            MAX_SENDS_PER_IP
        ):
            return (
                False,
                (
                    "Thiết bị này đã yêu cầu OTP "
                    "quá nhiều lần. "
                    "Vui lòng thử lại sau."
                ),
            )

        email_log.append(
            now
        )

        ip_log.append(
            now
        )

    return (
        True,
        "",
    )


# =========================================================
# GMAIL TOKEN PATH
# =========================================================

def get_gmail_token_path() -> Path:
    """
    Lấy đường dẫn gmail_token.json.

    Có thể cấu hình trong Environment Variables:

    GMAIL_TOKEN_PATH=
    C:\\BunChaVietSecrets\\gmail_token.json
    """

    configured = (
        os.getenv(
            "GMAIL_TOKEN_PATH"
        )
        or
        ""
    ).strip()

    if configured:
        return Path(
            configured
        )

    return (
        DEFAULT_GMAIL_TOKEN_PATH
    )


# =========================================================
# LOAD GMAIL OAUTH CREDENTIALS
# =========================================================

def load_gmail_credentials() -> Credentials:
    """
    Đọc gmail_token.json.

    Nếu access token hết hạn nhưng còn refresh token
    thì tự động refresh.
    """

    token_path = (
        get_gmail_token_path()
    )

    if not token_path.exists():

        raise RuntimeError(
            (
                "Không tìm thấy Gmail OAuth token tại: "
                f"{token_path}. "
                "Hãy chạy authorize_gmail.py trước."
            )
        )

    credentials = (
        Credentials
        .from_authorized_user_file(
            str(
                token_path
            ),
            SCOPES,
        )
    )

    # =====================================================
    # TOKEN HẾT HẠN -> REFRESH
    # =====================================================

    if (
        credentials.expired
        and
        credentials.refresh_token
    ):

        credentials.refresh(
            Request()
        )

        # Lưu access token mới
        token_path.write_text(
            credentials.to_json(),
            encoding="utf-8",
        )

    if not credentials.valid:

        raise RuntimeError(
            (
                "Gmail OAuth token không hợp lệ. "
                "Hãy chạy lại authorize_gmail.py."
            )
        )

    return credentials


# =========================================================
# SEND OTP THROUGH GMAIL API
# =========================================================

def send_gmail_otp(
    recipient: str,
    otp_code: str,
) -> None:
    """
    Gửi OTP thật bằng Gmail API.

    Không sử dụng:
    - SMTP
    - App Password
    - port 587
    - port 465
    """

    credentials = (
        load_gmail_credentials()
    )

    service = build(
        "gmail",
        "v1",
        credentials=credentials,
        cache_discovery=False,
    )

    sender = (
        os.getenv(
            "GMAIL_ADDRESS"
        )
        or
        ""
    ).strip()

    # =====================================================
    # EMAIL MESSAGE
    # =====================================================

    message = EmailMessage()

    if sender:

        message[
            "From"
        ] = (
            f"Bún Chả Việt <{sender}>"
        )

    message[
        "To"
    ] = recipient

    message[
        "Subject"
    ] = (
        f"{otp_code} là mã xác thực "
        "Bún Chả Việt"
    )

    # =====================================================
    # PLAIN TEXT VERSION
    # =====================================================

    message.set_content(
        (
            "Bún Chả Việt\n\n"
            f"Mã OTP của bạn là: "
            f"{otp_code}\n\n"
            "Mã có hiệu lực trong 5 phút.\n\n"
            "Nếu bạn không yêu cầu mã này, "
            "hãy bỏ qua email."
        )
    )

    # =====================================================
    # HTML VERSION
    # =====================================================

    message.add_alternative(
        f"""
        <!doctype html>

        <html lang="vi">

        <body
            style="
                margin: 0;
                padding: 30px;
                background: #f6f1ec;
                font-family: Arial, sans-serif;
                color: #2a211d;
            "
        >

            <div
                style="
                    max-width: 520px;
                    margin: auto;
                    background: #ffffff;
                    padding: 30px;
                    border-radius: 16px;
                    border: 1px solid #eadfd6;
                "
            >

                <h2
                    style="
                        margin-top: 0;
                        color: #8f0b24;
                    "
                >
                    Bún Chả Việt
                </h2>


                <p>
                    Bạn đang xác thực email
                    để đặt hàng.
                </p>


                <p>
                    Mã OTP của bạn là:
                </p>


                <div
                    style="
                        font-size: 34px;
                        font-weight: 700;
                        letter-spacing: 8px;
                        text-align: center;
                        padding: 20px;
                        margin: 20px 0;
                        background: #fff0f3;
                        border-radius: 12px;
                        color: #8f0b24;
                    "
                >
                    {otp_code}
                </div>


                <p>
                    Mã này có hiệu lực trong
                    <strong>
                        5 phút
                    </strong>.
                </p>


                <p
                    style="
                        color: #777;
                        font-size: 13px;
                    "
                >
                    Nếu bạn không yêu cầu mã này,
                    hãy bỏ qua email.
                </p>

            </div>

        </body>

        </html>
        """,
        subtype="html",
    )

    # =====================================================
    # BASE64URL FOR GMAIL API
    # =====================================================

    encoded_message = (
        base64
        .urlsafe_b64encode(
            message.as_bytes()
        )
        .decode(
            "utf-8"
        )
    )

    # =====================================================
    # SEND
    # =====================================================

    result = (
        service
        .users()
        .messages()
        .send(
            userId="me",
            body={
                "raw":
                    encoded_message
            },
        )
        .execute()
    )

    current_app.logger.info(
        (
            "Gmail OTP sent to %s. "
            "Message ID=%s"
        ),
        recipient,
        result.get(
            "id"
        ),
    )


# =========================================================
# CLEAR PENDING OTP
# =========================================================

def clear_pending_otp() -> None:
    """
    Xóa OTP đang chờ xác nhận.
    """

    for key in (
        "email_otp_email",
        "email_otp_hash",
        "email_otp_expires_at",
        "email_otp_attempts",
        "email_otp_last_sent_at",
    ):
        session.pop(
            key,
            None,
        )


# =========================================================
# CLEAR VERIFIED EMAIL
# =========================================================

def clear_verified_email() -> None:
    """
    Xóa trạng thái email đã xác thực.
    """

    session.pop(
        "checkout_verified_email",
        None,
    )

    session.pop(
        "checkout_verified_email_at",
        None,
    )


# =========================================================
# GET VERIFIED EMAIL
# =========================================================

def get_verified_email() -> str:
    """
    Trả về email đã verify.

    Nếu verify quá 15 phút thì
    tự động hết hiệu lực.
    """

    email = str(
        session.get(
            "checkout_verified_email"
        )
        or
        ""
    )

    verified_at = int(
        session.get(
            "checkout_verified_email_at"
        )
        or
        0
    )

    if (
        not email
        or
        verified_at <= 0
    ):
        return ""

    if (
        int(
            time.time()
        )
        -
        verified_at
        >
        OTP_VERIFY_SESSION_SECONDS
    ):

        clear_verified_email()

        return ""

    return email


# =========================================================
# API: SEND OTP
# =========================================================

@email_otp_bp.route(
    "/api/email-otp/send",
    methods=[
        "POST",
    ],
)
def send_email_otp(
) -> Response | tuple[
    Response,
    int,
]:
    """
    API gửi OTP.

    Request:
    {
        "email": "customer@gmail.com"
    }
    """

    data = (
        request.get_json(
            silent=True
        )
        or
        {}
    )

    # =====================================================
    # EMAIL
    # =====================================================

    try:

        email = normalize_email(
            str(
                data.get(
                    "email"
                )
                or
                ""
            )
        )

    except ValueError as error:

        return jsonify({
            "success":
                False,

            "message":
                str(
                    error
                ),
        }), 400

    now = int(
        time.time()
    )

    last_sent_at = int(
        session.get(
            "email_otp_last_sent_at"
        )
        or
        0
    )

    pending_email = str(
        session.get(
            "email_otp_email"
        )
        or
        ""
    )

    # =====================================================
    # RESEND COOLDOWN
    # =====================================================

    if (
        pending_email
        ==
        email
        and
        now
        -
        last_sent_at
        <
        OTP_RESEND_SECONDS
    ):

        retry_after = (
            OTP_RESEND_SECONDS
            -
            (
                now
                -
                last_sent_at
            )
        )

        return jsonify({
            "success":
                False,

            "message":
                (
                    f"Vui lòng chờ "
                    f"{retry_after} giây "
                    f"trước khi gửi lại OTP."
                ),

            "retryAfter":
                retry_after,
        }), 429

    # =====================================================
    # RATE LIMIT
    # =====================================================

    allowed, rate_message = (
        check_rate_limit(
            email,
            get_client_ip(),
        )
    )

    if not allowed:

        return jsonify({
            "success":
                False,

            "message":
                rate_message,
        }), 429

    # =====================================================
    # CREATE RANDOM OTP
    # =====================================================

    otp_code = (
        f"{secrets.randbelow(1_000_000):06d}"
    )

    # =====================================================
    # SEND THROUGH GMAIL API
    # =====================================================

    try:

        send_gmail_otp(
            email,
            otp_code,
        )

    except (
        HttpError,
        OSError,
        RuntimeError,
        ValueError,
    ) as error:

        current_app.logger.exception(
            (
                "Gmail API OTP "
                "send failed: %s"
            ),
            error,
        )

        return jsonify({
            "success":
                False,

            "message":
                (
                    "Không gửi được OTP qua email. "
                    "Vui lòng thử lại sau."
                ),
        }), 502

    # =====================================================
    # SAVE OTP SESSION
    # =====================================================

    clear_verified_email()

    session[
        "email_otp_email"
    ] = email

    session[
        "email_otp_hash"
    ] = hash_otp(
        email,
        otp_code,
    )

    session[
        "email_otp_expires_at"
    ] = (
        now
        +
        OTP_EXPIRES_SECONDS
    )

    session[
        "email_otp_attempts"
    ] = 0

    session[
        "email_otp_last_sent_at"
    ] = now

    return jsonify({
        "success":
            True,

        "message":
            "Mã OTP đã được gửi tới email.",

        "expiresIn":
            OTP_EXPIRES_SECONDS,

        "resendAfter":
            OTP_RESEND_SECONDS,
    })


# =========================================================
# API: VERIFY OTP
# =========================================================

@email_otp_bp.route(
    "/api/email-otp/verify",
    methods=[
        "POST",
    ],
)
def verify_email_otp(
) -> Response | tuple[
    Response,
    int,
]:
    """
    API xác nhận OTP.

    Request:
    {
        "email": "customer@gmail.com",
        "otp": "123456"
    }
    """

    data = (
        request.get_json(
            silent=True
        )
        or
        {}
    )

    # =====================================================
    # EMAIL
    # =====================================================

    try:

        email = normalize_email(
            str(
                data.get(
                    "email"
                )
                or
                ""
            )
        )

    except ValueError as error:

        return jsonify({
            "success":
                False,

            "message":
                str(
                    error
                ),
        }), 400

    # =====================================================
    # OTP
    # =====================================================

    otp_code = re.sub(
        r"\D",
        "",
        str(
            data.get(
                "otp"
            )
            or
            ""
        ),
    )

    if not re.fullmatch(
        r"\d{6}",
        otp_code,
    ):

        return jsonify({
            "success":
                False,

            "message":
                "OTP phải gồm đúng 6 chữ số.",
        }), 400

    # =====================================================
    # LOAD OTP SESSION
    # =====================================================

    pending_email = str(
        session.get(
            "email_otp_email"
        )
        or
        ""
    )

    stored_hash = str(
        session.get(
            "email_otp_hash"
        )
        or
        ""
    )

    expires_at = int(
        session.get(
            "email_otp_expires_at"
        )
        or
        0
    )

    attempts = int(
        session.get(
            "email_otp_attempts"
        )
        or
        0
    )

    # =====================================================
    # EMAIL MATCH
    # =====================================================

    if (
        not pending_email
        or
        pending_email != email
        or
        not stored_hash
    ):

        return jsonify({
            "success":
                False,

            "message":
                (
                    "Không tìm thấy OTP cho email này. "
                    "Vui lòng gửi mã mới."
                ),
        }), 400

    # =====================================================
    # EXPIRED
    # =====================================================

    if (
        int(
            time.time()
        )
        >
        expires_at
    ):

        clear_pending_otp()

        return jsonify({
            "success":
                False,

            "message":
                (
                    "OTP đã hết hạn. "
                    "Vui lòng gửi mã mới."
                ),
        }), 400

    # =====================================================
    # MAX WRONG ATTEMPTS
    # =====================================================

    if (
        attempts
        >=
        OTP_MAX_ATTEMPTS
    ):

        clear_pending_otp()

        return jsonify({
            "success":
                False,

            "message":
                (
                    "Bạn đã nhập sai OTP "
                    "quá nhiều lần. "
                    "Vui lòng gửi mã mới."
                ),
        }), 429

    # Tăng số lần thử
    session[
        "email_otp_attempts"
    ] = (
        attempts
        +
        1
    )

    provided_hash = (
        hash_otp(
            email,
            otp_code,
        )
    )

    # =====================================================
    # WRONG OTP
    # =====================================================

    if not hmac.compare_digest(
        stored_hash,
        provided_hash,
    ):

        remaining = max(
            (
                OTP_MAX_ATTEMPTS
                -
                attempts
                -
                1
            ),
            0,
        )

        return jsonify({
            "success":
                False,

            "message":
                (
                    f"Mã OTP không đúng. "
                    f"Bạn còn "
                    f"{remaining} lần thử."
                ),
        }), 400

    # =====================================================
    # VERIFIED
    # =====================================================

    clear_pending_otp()

    session[
        "checkout_verified_email"
    ] = email

    session[
        "checkout_verified_email_at"
    ] = int(
        time.time()
    )

    return jsonify({
        "success":
            True,

        "verified":
            True,

        "email":
            email,

        "message":
            "Xác thực email thành công.",
    })


# =========================================================
# API: CLEAR
# =========================================================

@email_otp_bp.route(
    "/api/email-otp/clear",
    methods=[
        "POST",
    ],
)
def clear_email_otp() -> Response:
    """
    Xóa OTP và trạng thái verified.
    """

    clear_pending_otp()

    clear_verified_email()

    return jsonify({
        "success":
            True,
    })


# =========================================================
# API: STATUS
# =========================================================

@email_otp_bp.route(
    "/api/email-otp/status",
    methods=[
        "GET",
    ],
)
def email_otp_status() -> Response:
    """
    Kiểm tra browser hiện tại
    đã verify email hay chưa.
    """

    email = (
        get_verified_email()
    )

    return jsonify({
        "success":
            True,

        "verified":
            bool(
                email
            ),

        "email":
            email
            or
            None,
    })


# =========================================================
# BACKEND ORDER GUARD
# =========================================================

@email_otp_bp.before_app_request
def require_verified_email_for_order(
) -> Response | tuple[
    Response,
    int,
] | None:
    """
    Chặn tạo đơn nếu email chưa được OTP verify.

    Đây là lớp bảo vệ thật.

    JavaScript frontend chỉ hỗ trợ UX.
    Người dùng có bypass JavaScript cũng
    không POST /api/orders được.
    """

    # Chỉ chặn đúng endpoint tạo đơn
    if (
        request.path
        !=
        "/api/orders"
        or
        request.method
        !=
        "POST"
    ):
        return None

    data = (
        request.get_json(
            silent=True
        )
        or
        {}
    )

    # =====================================================
    # EMAIL TRONG ORDER
    # =====================================================

    try:

        order_email = (
            normalize_email(
                str(
                    data.get(
                        "email"
                    )
                    or
                    ""
                )
            )
        )

    except ValueError as error:

        return jsonify({
            "success":
                False,

            "code":
                "INVALID_EMAIL",

            "message":
                str(
                    error
                ),
        }), 400

    verified_email = (
        get_verified_email()
    )

    # =====================================================
    # CHƯA VERIFY
    # =====================================================

    if not verified_email:

        return jsonify({
            "success":
                False,

            "code":
                "EMAIL_OTP_REQUIRED",

            "message":
                (
                    "Vui lòng xác thực email "
                    "bằng OTP trước khi đặt hàng."
                ),
        }), 403

    # =====================================================
    # ĐỔI EMAIL SAU KHI VERIFY
    # =====================================================

    if (
        verified_email
        !=
        order_email
    ):

        clear_verified_email()

        return jsonify({
            "success":
                False,

            "code":
                "EMAIL_CHANGED_AFTER_VERIFY",

            "message":
                (
                    "Email đặt hàng khác email "
                    "đã xác thực. "
                    "Vui lòng xác thực OTP lại."
                ),
        }), 403

    return None


# =========================================================
# ONE VERIFIED EMAIL = ONE SUCCESSFUL ORDER
# =========================================================

@email_otp_bp.after_app_request
def consume_verified_email_after_order(
    response: Response,
) -> Response:
    """
    Sau khi tạo đơn thành công,
    xóa trạng thái email verified.

    Nếu muốn đặt đơn mới,
    khách phải verify lại.
    """

    if (
        request.path
        ==
        "/api/orders"
        and
        request.method
        ==
        "POST"
        and
        response.status_code
        <
        300
    ):

        payload = (
            response.get_json(
                silent=True
            )
        )

        if (
            isinstance(
                payload,
                dict,
            )
            and
            payload.get(
                "success"
            )
            is True
        ):

            clear_verified_email()

    return response