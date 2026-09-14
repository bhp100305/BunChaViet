document.getElementById("loginForm").addEventListener("submit", async function (e) {
    e.preventDefault();

    const usernameInput = document.getElementById("username").value.trim();
    const passwordInput = document.getElementById("password").value.trim();
    const errorBox = document.getElementById("errorMessage");

    errorBox.style.display = "none";
    errorBox.textContent = "";

    try {
        const response = await fetch("/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username: usernameInput,
                password: passwordInput
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            // Đăng nhập thành công -> Chuyển hướng theo vai trò (Role)
            if (data.role === "Admin") {
                window.location.href = "/admin/dashboard";
            }
            else if(data.role === "Shipper") {
                window.location.href = "/shipper/orders";
            }

             else {
                window.location.href = "/staff/orders";
            }
        } else {
            // Báo lỗi nếu sai tài khoản / mật khẩu
            errorBox.textContent = data.message || "Tên đăng nhập hoặc mật khẩu không chính xác!";
            errorBox.style.display = "block";
        }
    } catch (err) {
        console.error("Lỗi khi kết nối tới máy chủ:", err);
        errorBox.textContent = "Không thể kết nối tới máy chủ. Vui lòng thử lại sau!";
        errorBox.style.display = "block";
    }
});