// =======================================
// LỌC ĐƠN HÀNG
// =======================================

function filterOrders() {

    const date = document.getElementById("filter-date").value;
    const month = document.getElementById("filter-month").value;
    const status = document.getElementById("filter-status").value;

    const params = new URLSearchParams();

    if (date) {
        params.append("date", date);
    } else if (month) {
        params.append("month", month);
    }

    if (status) {
        params.append("status", status);
    }

    const query = params.toString();

    window.location.href = query
        ? "/admin/orders?" + query
        : "/admin/orders";
}


// =======================================
// XÓA BỘ LỌC
// =======================================

function resetFilter() {

    window.location.href = "/admin/orders";
}


// =======================================
// KHI CHỌN NGÀY
// TỰ BỎ THÁNG
// =======================================

document
    .getElementById("filter-date")
    .addEventListener("change", function () {

        if (this.value) {
            document.getElementById("filter-month").value = "";
        }

    });


// =======================================
// KHI CHỌN THÁNG
// TỰ BỎ NGÀY
// =======================================

document
    .getElementById("filter-month")
    .addEventListener("change", function () {

        if (this.value) {
            document.getElementById("filter-date").value = "";
        }

    });


// =======================================
// CẬP NHẬT TRẠNG THÁI
// =======================================

document
    .querySelectorAll(".update-order-btn")
    .forEach(button => {

        button.addEventListener("click", async function () {

            const id = this.dataset.id;

            const status = document
                .getElementById("status-" + id)
                .value;

            try {

                const response = await fetch(
                    "/api/admin/orders/update/" + id,
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            status: status
                        })
                    }
                );

                const data = await response.json();

                if (data.success) {

                    alert(
                        "Cập nhật trạng thái thành công!"
                    );

                    location.reload();

                } else {

                    alert(
                        "Cập nhật trạng thái thất bại!"
                    );

                }

            } catch (error) {

                console.error(error);

                alert(
                    "Không thể kết nối tới máy chủ!"
                );

            }

        });

    });


// =======================================
// GIAO ĐƠN CHO SHIPPER
// =======================================

document
    .querySelectorAll(".assign-btn")
    .forEach(button => {

        button.addEventListener("click", async function () {

            const orderId = this.dataset.id;

            const select = this
                .parentElement
                .querySelector(".shipper-select");

            const driverId = select.value;

            if (!driverId) {

                alert(
                    "Vui lòng chọn shipper!"
                );

                return;

            }

            try {

                const response = await fetch(
                    "/admin/orders/assign",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            orderId: orderId,
                            driverId: driverId
                        })
                    }
                );

                const data = await response.json();

                if (data.success) {

                    alert(
                        "Đã giao đơn cho shipper!"
                    );

                    location.reload();

                } else {

                    alert(
                        data.message ||
                        "Không thể giao đơn!"
                    );

                }

            } catch (error) {

                console.error(error);

                alert(
                    "Không thể kết nối tới máy chủ!"
                );

            }

        });

    });