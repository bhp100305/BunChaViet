document.addEventListener(
    "DOMContentLoaded",
    () => {

        // =====================================================
        // ELEMENTS
        // =====================================================

        const loginForm =
            document.getElementById(
                "loginForm"
            );


        const usernameInput =
            document.getElementById(
                "username"
            );


        const passwordInput =
            document.getElementById(
                "password"
            );


        const errorBox =
            document.getElementById(
                "errorMessage"
            );


        if (
            !loginForm
            ||
            !usernameInput
            ||
            !passwordInput
            ||
            !errorBox
        ) {

            console.error(
                "Thiếu element của form đăng nhập."
            );

            return;

        }


        // =====================================================
        // HIỂN THỊ LÝ DO BỊ ĐĂNG XUẤT
        // =====================================================

        showLoginReason(
            errorBox
        );


        // =====================================================
        // SUBMIT LOGIN
        // =====================================================

        loginForm.addEventListener(
            "submit",
            async (event) => {

                event.preventDefault();


                // =============================================
                // RESET ERROR
                // =============================================

                hideError(
                    errorBox
                );


                const username =
                    usernameInput.value.trim();


                /*
                 * Không trim password.
                 *
                 * Nếu mật khẩu thật có khoảng trắng đầu/cuối
                 * thì trim() sẽ biến nó thành mật khẩu khác.
                 */

                const password =
                    passwordInput.value;


                // =============================================
                // VALIDATE
                // =============================================

                if (!username) {

                    showError(
                        errorBox,
                        "Vui lòng nhập tên đăng nhập."
                    );


                    usernameInput.focus();


                    return;

                }


                if (!password) {

                    showError(
                        errorBox,
                        "Vui lòng nhập mật khẩu."
                    );


                    passwordInput.focus();


                    return;

                }


                // =============================================
                // DISABLE BUTTON
                // =============================================

                const submitButton =
                    loginForm.querySelector(
                        'button[type="submit"]'
                    );


                const oldButtonContent =
                    submitButton
                        ? submitButton.innerHTML
                        : "";


                if (submitButton) {

                    submitButton.disabled =
                        true;


                    submitButton.textContent =
                        "Đang đăng nhập...";

                }


                try {

                    // =========================================
                    // LOGIN REQUEST
                    // =========================================

                    const response =
                        await fetch(
                            "/login",
                            {

                                method:
                                    "POST",

                                credentials:
                                    "same-origin",

                                headers: {

                                    "Content-Type":
                                        "application/json"

                                },

                                body:
                                    JSON.stringify({

                                        username:
                                            username,

                                        password:
                                            password

                                    })

                            }
                        );


                    const data =
                        await readJsonResponse(
                            response
                        );


                    // =========================================
                    // LOGIN FAILED
                    // =========================================

                    if (
                        !response.ok
                        ||
                        !data.success
                    ) {

                        showError(

                            errorBox,

                            data.message
                            ||
                            "Tên đăng nhập hoặc mật khẩu không chính xác!"

                        );


                        return;

                    }


                    // =========================================
                    // LOGIN SUCCESS
                    // =========================================

                    redirectByRole(
                        data.role
                    );

                }
                catch (error) {

                    console.error(
                        "Lỗi khi kết nối tới máy chủ:",
                        error
                    );


                    showError(

                        errorBox,

                        "Không thể kết nối tới máy chủ. "
                        +
                        "Vui lòng thử lại sau!"

                    );

                }
                finally {

                    /*
                     * Nếu redirect đã xảy ra thì phần này cũng không gây vấn đề.
                     *
                     * Nếu login lỗi thì nút được bật lại.
                     */

                    if (submitButton) {

                        submitButton.disabled =
                            false;


                        submitButton.innerHTML =
                            oldButtonContent;

                    }

                }

            }
        );

    }
);


// =========================================================
// REDIRECT THEO ROLE
// =========================================================

function redirectByRole(
    role
) {

    switch (
        role
    ) {

        case "Admin":

            window.location.href =
                "/admin/dashboard";

            break;


        case "Shipper":

            /*
             * Khi tới đây:
             *
             * backend đã tạo shipper_session_token mới
             * và ghi token đó vào Users.ActiveSessionToken.
             *
             * Nếu cùng tài khoản đang chạy trên máy khác,
             * máy cũ sẽ bị invalid.
             */

            window.location.href =
                "/shipper/orders";

            break;


        case "Staff":

            window.location.href =
                "/staff/orders";

            break;


        default:

            /*
             * Role khác thì tạm đưa về staff.
             *
             * Có thể đổi sau nếu hệ thống có thêm role.
             */

            window.location.href =
                "/staff/orders";

            break;

    }

}


// =========================================================
// SHOW LOGIN REASON
// =========================================================

function showLoginReason(
    errorBox
) {

    const params =
        new URLSearchParams(
            window.location.search
        );


    const reason =
        params.get(
            "reason"
        );


    if (!reason) {

        return;

    }


    let message =
        "";


    switch (
        reason
    ) {

        // =================================================
        // LOGIN TRÊN MÁY KHÁC
        // =================================================

        case "session_conflict":

            message =
                "Tài khoản Shipper vừa được đăng nhập "
                +
                "trên một thiết bị khác. "
                +
                "Phiên trên thiết bị này đã bị ngắt "
                +
                "để tránh xung đột GPS.";

            break;


        // =================================================
        // TÀI KHOẢN BỊ KHÓA
        // =================================================

        case "account_locked":

            message =
                "Tài khoản Shipper đã bị khóa. "
                +
                "Vui lòng liên hệ quản trị viên.";

            break;


        // =================================================
        // SESSION KHÔNG HỢP LỆ
        // =================================================

        case "session_invalid":

            message =
                "Phiên đăng nhập đã hết hiệu lực. "
                +
                "Vui lòng đăng nhập lại.";

            break;


        default:

            return;

    }


    showError(
        errorBox,
        message
    );


    /*
     * Xóa ?reason=... khỏi URL sau khi đã hiện thông báo.
     *
     * Nếu user F5 sẽ không bị hiện thông báo cũ mãi mãi.
     */

    const cleanUrl =
        window.location.pathname;


    window.history.replaceState(
        {},
        document.title,
        cleanUrl
    );

}


// =========================================================
// SHOW ERROR
// =========================================================

function showError(
    errorBox,
    message
) {

    if (!errorBox) {

        return;

    }


    errorBox.textContent =
        message;


    errorBox.style.display =
        "block";

}


// =========================================================
// HIDE ERROR
// =========================================================

function hideError(
    errorBox
) {

    if (!errorBox) {

        return;

    }


    errorBox.textContent =
        "";


    errorBox.style.display =
        "none";

}


// =========================================================
// SAFE JSON
// =========================================================

async function readJsonResponse(
    response
) {

    try {

        return await response.json();

    }
    catch (error) {

        console.error(
            "Server trả về response không phải JSON:",
            error
        );


        return {

            success:
                false,

            message:
                "Máy chủ trả về dữ liệu không hợp lệ."

        };

    }

}