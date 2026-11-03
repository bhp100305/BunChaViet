// =========================================================
// BUN CHA VIET - EMAIL OTP
// =========================================================

let emailOtpVerified = false;
let verifiedOrderEmail = "";

let emailOtpResendTimer = null;


// =========================================================
// DOM
// =========================================================

const emailOtpEmailInput =
    document.getElementById(
        "email"
    );


const sendEmailOtpButton =
    document.getElementById(
        "send-email-otp-btn"
    );


const emailOtpPanel =
    document.getElementById(
        "email-otp-panel"
    );


const emailOtpCodeInput =
    document.getElementById(
        "email-otp-code"
    );


const verifyEmailOtpButton =
    document.getElementById(
        "verify-email-otp-btn"
    );


const emailOtpStatus =
    document.getElementById(
        "email-otp-status"
    );


// =========================================================
// NORMALIZE EMAIL
// =========================================================

function normalizeEmail(
    value
) {

    const email =
        String(
            value
            ||
            ""
        )
        .trim()
        .toLowerCase();


    if (
        !email
    ) {

        return "";

    }


    const emailPattern =
        /^[^\s@]+@[^\s@]+\.[^\s@]+$/;


    if (
        !emailPattern.test(
            email
        )
    ) {

        return "";

    }


    return email;

}


// =========================================================
// SET STATUS
// =========================================================

function setEmailOtpStatus(
    message,
    type = "pending"
) {

    if (
        !emailOtpStatus
    ) {

        return;

    }


    emailOtpStatus.textContent =
        message;


    emailOtpStatus.className =
        `email-otp-status is-${type}`;

}


// =========================================================
// READ JSON SAFELY
// =========================================================

async function readEmailOtpJson(
    response
) {

    try {

        return await response.json();

    }
    catch (
        error
    ) {

        console.error(
            "Email OTP JSON error:",
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


// =========================================================
// CLEAR SERVER VERIFICATION
// =========================================================

async function clearEmailVerification() {

    try {

        await fetch(
            "/api/email-otp/clear",
            {

                method:
                    "POST",

                credentials:
                    "same-origin"

            }
        );

    }
    catch (
        error
    ) {

        console.warn(
            "Không xóa được OTP session:",
            error
        );

    }

}


// =========================================================
// RESET OTP STATE
// =========================================================

function resetEmailOtpState(
    message =
        "Email chưa được xác thực."
) {

    emailOtpVerified =
        false;


    verifiedOrderEmail =
        "";


    if (
        emailOtpCodeInput
    ) {

        emailOtpCodeInput.value =
            "";

    }


    if (
        emailOtpPanel
    ) {

        emailOtpPanel.hidden =
            true;

    }


    setEmailOtpStatus(
        message,
        "pending"
    );

}


// =========================================================
// RESEND COUNTDOWN
// =========================================================

function startEmailOtpCountdown(
    seconds = 60
) {

    if (
        !sendEmailOtpButton
    ) {

        return;

    }


    if (
        emailOtpResendTimer
    ) {

        window.clearInterval(
            emailOtpResendTimer
        );

    }


    let remaining =
        Math.max(
            Number(
                seconds
            )
            ||
            0,
            0
        );


    sendEmailOtpButton.disabled =
        true;


    sendEmailOtpButton.textContent =
        `Gửi lại sau ${remaining}s`;


    emailOtpResendTimer =
        window.setInterval(
            () => {

                remaining -= 1;


                if (
                    remaining <= 0
                ) {

                    window.clearInterval(
                        emailOtpResendTimer
                    );


                    emailOtpResendTimer =
                        null;


                    sendEmailOtpButton.disabled =
                        false;


                    sendEmailOtpButton.textContent =
                        "Gửi OTP";


                    return;

                }


                sendEmailOtpButton.textContent =
                    `Gửi lại sau ${remaining}s`;

            },
            1000
        );

}


// =========================================================
// SEND OTP
// =========================================================

sendEmailOtpButton?.addEventListener(
    "click",
    async () => {

        const email =
            normalizeEmail(
                emailOtpEmailInput?.value
            );


        if (
            !email
        ) {

            alert(
                "Vui lòng nhập địa chỉ email hợp lệ."
            );


            emailOtpEmailInput?.focus();


            return;

        }


        const originalText =
            sendEmailOtpButton.textContent;


        sendEmailOtpButton.disabled =
            true;


        sendEmailOtpButton.textContent =
            "Đang gửi...";


        resetEmailOtpState(
            "Đang gửi OTP tới email..."
        );


        try {

            const response =
                await fetch(
                    "/api/email-otp/send",
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

                                email:
                                    email

                            })

                    }
                );


            const data =
                await readEmailOtpJson(
                    response
                );


            if (
                !response.ok
                ||
                !data.success
            ) {

                throw new Error(

                    data.message

                    ||

                    "Không gửi được OTP."

                );

            }


            if (
                emailOtpPanel
            ) {

                emailOtpPanel.hidden =
                    false;

            }


            setEmailOtpStatus(

                `Đã gửi OTP tới ${email}. Mã có hiệu lực trong 5 phút.`,

                "sent"

            );


            emailOtpCodeInput?.focus();


            startEmailOtpCountdown(
                data.resendAfter
                ||
                60
            );

        }
        catch (
            error
        ) {

            console.error(
                "Send email OTP error:",
                error
            );


            sendEmailOtpButton.disabled =
                false;


            sendEmailOtpButton.textContent =
                originalText
                ||
                "Gửi OTP";


            setEmailOtpStatus(

                error.message

                ||

                "Không gửi được OTP.",

                "error"

            );

        }

    }
);


// =========================================================
// VERIFY OTP
// =========================================================

verifyEmailOtpButton?.addEventListener(
    "click",
    async () => {

        const email =
            normalizeEmail(
                emailOtpEmailInput?.value
            );


        const otp =
            String(
                emailOtpCodeInput?.value
                ||
                ""
            )
            .replace(
                /\D/g,
                ""
            )
            .slice(
                0,
                6
            );


        if (
            !email
        ) {

            alert(
                "Email không hợp lệ."
            );


            emailOtpEmailInput?.focus();


            return;

        }


        if (
            !/^\d{6}$/.test(
                otp
            )
        ) {

            alert(
                "Mã OTP phải gồm đúng 6 chữ số."
            );


            emailOtpCodeInput?.focus();


            return;

        }


        const originalText =
            verifyEmailOtpButton.textContent;


        verifyEmailOtpButton.disabled =
            true;


        verifyEmailOtpButton.textContent =
            "Đang xác nhận...";


        try {

            const response =
                await fetch(
                    "/api/email-otp/verify",
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

                                email:
                                    email,

                                otp:
                                    otp

                            })

                    }
                );


            const data =
                await readEmailOtpJson(
                    response
                );


            if (
                !response.ok
                ||
                !data.success
            ) {

                throw new Error(

                    data.message

                    ||

                    "OTP không đúng."

                );

            }


            emailOtpVerified =
                true;


            verifiedOrderEmail =
                email;


            setEmailOtpStatus(

                `✓ Đã xác thực ${email}. Bạn có thể đặt hàng.`,

                "verified"

            );


            if (
                emailOtpPanel
            ) {

                emailOtpPanel.hidden =
                    true;

            }


            if (
                emailOtpEmailInput
            ) {

                emailOtpEmailInput.dataset.verified =
                    "true";

            }

        }
        catch (
            error
        ) {

            console.error(
                "Verify email OTP error:",
                error
            );


            emailOtpVerified =
                false;


            verifiedOrderEmail =
                "";


            if (
                emailOtpEmailInput
            ) {

                emailOtpEmailInput.dataset.verified =
                    "false";

            }


            setEmailOtpStatus(

                error.message

                ||

                "Không xác thực được OTP.",

                "error"

            );

        }
        finally {

            verifyEmailOtpButton.disabled =
                false;


            verifyEmailOtpButton.textContent =
                originalText
                ||
                "Xác nhận OTP";

        }

    }
);


// =========================================================
// EMAIL CHANGED AFTER VERIFY
// =========================================================

emailOtpEmailInput?.addEventListener(
    "input",
    async () => {

        const currentEmail =
            normalizeEmail(
                emailOtpEmailInput.value
            );


        if (
            emailOtpVerified
            &&
            currentEmail
            !==
            verifiedOrderEmail
        ) {

            resetEmailOtpState(
                "Bạn đã thay đổi email. Vui lòng xác thực OTP lại."
            );


            emailOtpEmailInput.dataset.verified =
                "false";


            await clearEmailVerification();

        }

    }
);


// =========================================================
// OTP INPUT ONLY NUMBERS
// =========================================================

emailOtpCodeInput?.addEventListener(
    "input",
    () => {

        emailOtpCodeInput.value =
            emailOtpCodeInput.value
            .replace(
                /\D/g,
                ""
            )
            .slice(
                0,
                6
            );

    }
);


// =========================================================
// ENTER = VERIFY OTP
// =========================================================

emailOtpCodeInput?.addEventListener(
    "keydown",
    (
        event
    ) => {

        if (
            event.key ===
            "Enter"
        ) {

            event.preventDefault();


            verifyEmailOtpButton?.click();

        }

    }
);


// =========================================================
// CHECK EXISTING VERIFIED SESSION
// =========================================================

async function restoreEmailOtpStatus() {

    try {

        const response =
            await fetch(
                "/api/email-otp/status",
                {

                    method:
                        "GET",

                    credentials:
                        "same-origin"

                }
            );


        const data =
            await readEmailOtpJson(
                response
            );


        if (
            !response.ok
            ||
            !data.success
            ||
            !data.verified
            ||
            !data.email
        ) {

            return;

        }


        const currentEmail =
            normalizeEmail(
                emailOtpEmailInput?.value
            );


        if (
            currentEmail
            &&
            currentEmail
            ===
            data.email
        ) {

            emailOtpVerified =
                true;


            verifiedOrderEmail =
                data.email;


            if (
                emailOtpEmailInput
            ) {

                emailOtpEmailInput.dataset.verified =
                    "true";

            }


            setEmailOtpStatus(

                `✓ Email ${data.email} đã được xác thực.`,

                "verified"

            );

        }

    }
    catch (
        error
    ) {

        console.warn(
            "Không kiểm tra được OTP status:",
            error
        );

    }

}


// =========================================================
// FRONTEND ORDER GUARD
// =========================================================

document.addEventListener(

    "click",

    (
        event
    ) => {

        const target =
            event.target;


        if (
            !(
                target
                instanceof
                Element
            )
        ) {

            return;

        }


        const orderButton =
            target.closest(
                "#order-btn"
            );


        if (
            !orderButton
        ) {

            return;

        }


        const currentEmail =
            normalizeEmail(
                emailOtpEmailInput?.value
            );


        if (
            !emailOtpVerified
            ||
            !currentEmail
            ||
            currentEmail
            !==
            verifiedOrderEmail
        ) {

            event.preventDefault();


            event.stopImmediatePropagation();


            alert(
                "Vui lòng xác thực email bằng OTP trước khi đặt hàng."
            );


            emailOtpEmailInput?.focus();

        }

    },

    true

);


// =========================================================
// PAGE LOAD
// =========================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        setEmailOtpStatus(
            "Email chưa được xác thực.",
            "pending"
        );


        restoreEmailOtpStatus();

    }
);