const modal = document.getElementById("shipperModal");
const form = document.getElementById("shipperForm");

const shipperId = document.getElementById("shipperId");
const fullname = document.getElementById("fullname");
const username = document.getElementById("username");
const password = document.getElementById("password");
const phone = document.getElementById("phone");

const modalTitle = document.getElementById("modalTitle");


// =======================================
// MỞ FORM THÊM SHIPPER
// =======================================

document.getElementById("btnAddShipper").addEventListener("click", () => {
    form.reset();
    shipperId.value = "";
    modalTitle.textContent = "Thêm shipper";
    modal.classList.add("active");
});


// =======================================
// ĐÓNG FORM
// =======================================

document.getElementById("btnClose").addEventListener("click", () => {
    modal.classList.remove("active");
});

modal.addEventListener("click", (event) => {
    if (event.target === modal) {
        modal.classList.remove("active");
    }
});


// =======================================
// SỬA SHIPPER
// =======================================

document.querySelectorAll(".edit-btn").forEach(button => {
    button.addEventListener("click", () => {
        shipperId.value = button.dataset.id;
        fullname.value = button.dataset.fullname;
        username.value = button.dataset.username;
        phone.value = button.dataset.phone;

        password.value = "";

        modalTitle.textContent = "Sửa thông tin shipper";
        modal.classList.add("active");
    });
});


// =======================================
// THÊM / CẬP NHẬT SHIPPER
// =======================================

form.addEventListener("submit", async event => {
    event.preventDefault();

    const id = shipperId.value;

    const data = {
        fullname: fullname.value.trim(),
        username: username.value.trim(),
        password: password.value,
        phone: phone.value.trim()
    };

    const url = id
        ? `/admin/shippers/update/${id}`
        : "/admin/shippers/add";

    try {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (!result.success) {
            alert(result.message || "Có lỗi xảy ra!");
            return;
        }

        alert(id
            ? "Cập nhật shipper thành công!"
            : "Thêm shipper thành công!"
        );

        location.reload();

    } catch (error) {
        console.error(error);
        alert("Không thể kết nối tới máy chủ!");
    }
});


// =======================================
// KHÓA SHIPPER
// =======================================

document.querySelectorAll(".lock-btn").forEach(button => {
    button.addEventListener("click", async () => {
        const id = button.dataset.id;

        const confirmed = confirm(
            "Bạn có chắc muốn khóa tài khoản shipper này?"
        );

        if (!confirmed) {
            return;
        }

        await changeShipperStatus(id, 0);
    });
});


// =======================================
// MỞ KHÓA SHIPPER
// =======================================

document.querySelectorAll(".unlock-btn").forEach(button => {
    button.addEventListener("click", async () => {
        const id = button.dataset.id;

        await changeShipperStatus(id, 1);
    });
});


// =======================================
// THAY ĐỔI TRẠNG THÁI
// =======================================

async function changeShipperStatus(id, status) {
    try {
        const response = await fetch(
            `/admin/shippers/status/${id}`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    isActive: status
                })
            }
        );

        const result = await response.json();

        if (!result.success) {
            alert(result.message || "Không thể cập nhật!");
            return;
        }

        location.reload();

    } catch (error) {
        console.error(error);
        alert("Không thể kết nối tới máy chủ!");
    }
}