(() => {
    const form = document.getElementById("login-form");
    const message = document.getElementById("auth-message");
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!form.reportValidity()) return;
        const submit = form.querySelector("button[type=submit]");
        submit.disabled = true;
        message.textContent = "";
        try {
            const response = await fetch("/api/customer/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(Object.fromEntries(new FormData(form)))
            });
            const data = await response.json();
            if (!response.ok || !data.success) throw new Error(data.message || "Đăng nhập không thành công.");
            window.location.assign(data.redirect || "/");
        } catch (error) {
            message.textContent = error.message;
            message.classList.add("is-error");
        } finally {
            submit.disabled = false;
        }
    });
})();
