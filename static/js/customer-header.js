(() => {
    const nav = document.querySelector(".header nav, .header-content");
    if (!nav) return;
    fetch("/api/customer/session", { credentials: "same-origin" })
        .then((response) => response.json())
        .then((data) => {
            let link = nav.querySelector(".customer-account-link");
            if (!link) {
                link = document.createElement("a");
                link.className = "nav-link customer-account-link";
            }
            if (data.authenticated) {
                const customerName = data.customer.name || "";
                link.href = "/customer/profile";
                link.title = `Tài khoản: ${customerName}`;
                const updateAccountLabel = () => {
                    link.textContent = window.matchMedia("(max-width: 600px)").matches
                        ? "Tài khoản"
                        : `Tài khoản: ${customerName}`;
                };
                updateAccountLabel();
                window.addEventListener("resize", updateAccountLabel, { passive: true });
                const cart = nav.querySelector(".cart-btn");
                if (cart) cart.after(link);
                else if (link.parentElement !== nav) nav.append(link);
                const logout = document.createElement("button");
                logout.type = "button";
                logout.className = "nav-link customer-logout-link";
                logout.style.cssText = "border:0;background:transparent;font:inherit;cursor:pointer;padding:0;white-space:nowrap";
                logout.textContent = "Đăng xuất";
                logout.addEventListener("click", async () => {
                    await fetch("/api/customer/logout", { method: "POST", credentials: "same-origin" });
                    window.location.reload();
                });
                link.after(logout);
            } else {
                link.href = "/customer/login";
                link.textContent = "Đăng nhập";
                const cart = nav.querySelector(".cart-btn");
                if (cart) cart.after(link);
                else if (link.parentElement !== nav) nav.append(link);
            }
        })
        .catch(() => {});
})();
