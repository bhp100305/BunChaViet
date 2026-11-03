from __future__ import annotations

import base64
from email.message import EmailMessage
from email.utils import formatdate
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/gmail.send"
]

TOKEN_PATH = Path(
    r"C:\BunChaVietSecrets\gmail_token.json"
)


SENDER_EMAIL = (
    "footballgaming983@gmail.com"
)

RECEIVER_EMAIL = (
    "thuongbt67wru@gmail.com"
)


def main() -> None:
    """Test gửi email thật bằng Gmail API."""

    if not TOKEN_PATH.exists():
        raise FileNotFoundError(
            f"Không tìm thấy token: {TOKEN_PATH}"
        )

    credentials = (
        Credentials.from_authorized_user_file(
            str(TOKEN_PATH),
            SCOPES,
        )
    )

    service = build(
        "gmail",
        "v1",
        credentials=credentials,
    )

    message = EmailMessage()

    message["From"] = (
        f"Bún Chả Việt <{SENDER_EMAIL}>"
    )

    message["To"] = (
        RECEIVER_EMAIL
    )

    message["Subject"] = (
        "Test Gmail API - Bún Chả Việt"
    )

    message["Date"] = (
        formatdate(
            localtime=True
        )
    )

    message.set_content(
        (
            "Xin chào,\n\n"
            "Đây là email test từ website "
            "Bún Chả Việt.\n\n"
            "Nếu bạn nhận được email này "
            "thì Gmail API đã hoạt động "
            "thành công."
        )
    )

    encoded_message = (
        base64.urlsafe_b64encode(
            message.as_bytes()
        )
        .decode(
            "utf-8"
        )
    )

    result = (
        service
        .users()
        .messages()
        .send(
            userId="me",
            body={
                "raw": encoded_message
            },
        )
        .execute()
    )

    print(
        "GUI EMAIL THANH CONG"
    )

    print(
        "FROM:",
        SENDER_EMAIL
    )

    print(
        "TO:",
        RECEIVER_EMAIL
    )

    print(
        "Message ID:",
        result.get(
            "id"
        )
    )

    print(
        "Thread ID:",
        result.get(
            "threadId"
        )
    )


if __name__ == "__main__":
    main()