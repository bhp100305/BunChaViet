(() => {
    const form = document.getElementById("register-form");
    const emailInput = document.getElementById("register-email");
    const otpFields = document.getElementById("otp-fields");
    const message = document.getElementById("auth-message");
    let verifiedEmail = "";

    const showMessage = (text, error = false) => {
        message.textContent = text;
        message.classList.toggle("is-error", error);
        message.classList.toggle("is-success", !error && Boolean(text));
    };
    const post = async (url, body) => {
        const response = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
        const data = await response.json();
        if (!response.ok || !data.success) throw new Error(data.message || "Có lỗi xảy ra. Vui lòng thử lại.");
        return data;
    };
    const clearVerification = () => {
        verifiedEmail = "";
        otpFields.hidden = true;
        fetch("/api/email-otp/clear", { method: "POST" }).catch(() => {});
    };

    emailInput.addEventListener("input", () => {
        if (verifiedEmail && emailInput.value.trim().toLowerCase() !== verifiedEmail) {
            clearVerification();
            showMessage("Email đã thay đổi. Hãy xác thực email mới.", true);
        }
    });

    document.getElementById("send-otp").addEventListener("click", async (event) => {
        const email = emailInput.value.trim().toLowerCase();
        if (!emailInput.reportValidity()) return;
        event.currentTarget.disabled = true;
        try {
            await post("/api/email-otp/send", { email });
            otpFields.hidden = false;
            showMessage("Mã OTP đã được gửi đến email của bạn.");
        } catch (error) {
            showMessage(error.message, true);
        } finally {
            event.currentTarget.disabled = false;
        }
    });

    document.getElementById("verify-otp").addEventListener("click", async (event) => {
        event.currentTarget.disabled = true;
        try {
            const email = emailInput.value.trim().toLowerCase();
            await post("/api/email-otp/verify", { email, otp: document.getElementById("otp-code").value.trim() });
            verifiedEmail = email;
            showMessage("Email đã được xác thực. Bạn có thể đăng ký.");
        } catch (error) {
            showMessage(error.message, true);
        } finally {
            event.currentTarget.disabled = false;
        }
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!form.reportValidity()) return;
        const values = Object.fromEntries(new FormData(form));
        try {
            const data = await post("/api/customer/register", values);
            showMessage(data.message);
            window.location.assign(data.redirect || "/customer/login");
        } catch (error) {
            showMessage(error.message, true);
        }
    });
})();
