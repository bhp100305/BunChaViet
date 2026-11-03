(() => {
    const profileForm = document.getElementById("profile-form");
    const passwordForm = document.getElementById("password-form");

    const setMessage = (element, text = "", error = false) => {
        element.textContent = text;
        element.classList.toggle("is-error", error);
        element.classList.toggle("is-success", Boolean(text) && !error);
    };

    const request = async (url, options = {}) => {
        const response = await fetch(url, {
            credentials: "same-origin",
            ...options,
            headers: {
                ...(options.body ? { "Content-Type": "application/json" } : {}),
                ...(options.headers || {}),
            },
        });
        const data = await response.json();
        if (response.status === 401) {
            window.location.assign("/customer/login");
            throw new Error("Phiên đăng nhập đã hết hạn.");
        }
        if (!response.ok || !data.success) {
            throw new Error(data.message || "Có lỗi xảy ra. Vui lòng thử lại.");
        }
        return data;
    };

    request("/api/customer/profile")
        .then(({ profile }) => {
            document.getElementById("profile-name").value = profile.fullName;
            document.getElementById("profile-phone").value = profile.phone;
            document.getElementById("profile-email").value = profile.email;
        })
        .catch((error) => {
            if (window.location.pathname !== "/customer/login") {
                setMessage(document.getElementById("profile-message"), error.message, true);
            }
        });

    profileForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!profileForm.reportValidity()) return;
        const button = profileForm.querySelector("button[type=submit]");
        const message = document.getElementById("profile-message");
        button.disabled = true;
        setMessage(message);
        try {
            const data = await request("/api/customer/profile", {
                method: "PUT",
                body: JSON.stringify({
                    fullName: document.getElementById("profile-name").value.trim(),
                    phone: document.getElementById("profile-phone").value.trim(),
                }),
            });
            setMessage(message, data.message);
        } catch (error) {
            setMessage(message, error.message, true);
        } finally {
            button.disabled = false;
        }
    });

    passwordForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!passwordForm.reportValidity()) return;
        const message = document.getElementById("password-message");
        const currentPassword = document.getElementById("current-password").value;
        const newPassword = document.getElementById("new-password").value;
        const confirmPassword = document.getElementById("confirm-password").value;
        if (newPassword !== confirmPassword) {
            setMessage(message, "Mật khẩu nhập lại chưa khớp.", true);
            return;
        }
        const button = passwordForm.querySelector("button[type=submit]");
        button.disabled = true;
        setMessage(message);
        try {
            const data = await request("/api/customer/password", {
                method: "POST",
                body: JSON.stringify({ currentPassword, newPassword }),
            });
            passwordForm.reset();
            setMessage(message, data.message);
        } catch (error) {
            setMessage(message, error.message, true);
        } finally {
            button.disabled = false;
        }
    });

    document.getElementById("profile-logout").addEventListener("click", async () => {
        try {
            await request("/api/customer/logout", { method: "POST" });
        } finally {
            window.location.assign("/");
        }
    });
})();
