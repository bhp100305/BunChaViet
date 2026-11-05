from __future__ import annotations

from pathlib import Path
import os

from dotenv import load_dotenv
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


# =========================================================
# CONFIG
# =========================================================

load_dotenv(Path(__file__).resolve().with_name(".env"))

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send"
]


CREDENTIALS_PATH = Path(
    os.getenv("GMAIL_CREDENTIALS_PATH") or r"C:\BunChaVietSecrets\gmail_credentials.json"
)


TOKEN_PATH = Path(
    os.getenv("GMAIL_TOKEN_PATH") or r"C:\BunChaVietSecrets\gmail_token.json"
)


# =========================================================
# AUTHORIZE
# =========================================================

def main() -> None:
    """Authorize Gmail API and create refresh token."""

    credentials: Credentials | None = None

    # -----------------------------------------------------
    # LOAD EXISTING TOKEN
    # -----------------------------------------------------

    if TOKEN_PATH.exists():

        credentials = (
            Credentials.from_authorized_user_file(
                str(TOKEN_PATH),
                SCOPES,
            )
        )

    # -----------------------------------------------------
    # CREATE / REFRESH TOKEN
    # -----------------------------------------------------

    if (
        not credentials
        or
        not credentials.valid
    ):

        if (
            credentials
            and
            credentials.expired
            and
            credentials.refresh_token
        ):

            print(
                "Đang refresh Gmail token..."
            )

            try:
                credentials.refresh(Request())
            except RefreshError:
                print("Quyền Gmail đã hết hạn hoặc bị thu hồi. Cần đăng nhập Google lại.")
                credentials = None

        if not credentials or not credentials.valid:

            if not CREDENTIALS_PATH.exists():

                raise FileNotFoundError(
                    f"Không tìm thấy: "
                    f"{CREDENTIALS_PATH}"
                )

            print(
                "Đang mở trình duyệt để đăng nhập Google..."
            )

            flow = (
                InstalledAppFlow
                .from_client_secrets_file(
                    str(
                        CREDENTIALS_PATH
                    ),
                    SCOPES,
                )
            )

            credentials = (
                flow.run_local_server(
                    port=0,
                    open_browser=True,
                    prompt="consent",
                )
            )

        # -------------------------------------------------
        # SAVE TOKEN
        # -------------------------------------------------

        TOKEN_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        TOKEN_PATH.write_text(
            credentials.to_json(),
            encoding="utf-8",
        )

        print(
            "Đã tạo Gmail token:"
        )

        print(
            TOKEN_PATH
        )

    else:

        print(
            "Gmail token hiện tại vẫn hợp lệ."
        )

    print(
        ""
    )

    print(
        "GMAIL OAUTH OK"
    )


if __name__ == "__main__":
    main()
