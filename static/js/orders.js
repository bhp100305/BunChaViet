// =========================================================
// ADMIN ORDER MANAGEMENT
// BUN CHA VIET
// =========================================================


document.addEventListener(
    "DOMContentLoaded",
    function () {

        setupFilters();

        setupAssignButtons();

        setupOrderStatusButtons();

        setupDateMonthBehavior();

    }
);


// =========================================================
// FILTER
// =========================================================

function setupFilters() {

    const filterButton =
        document.getElementById(
            "filterOrdersBtn"
        );


    const resetButton =
        document.getElementById(
            "resetFilterBtn"
        );


    if (filterButton) {

        filterButton.addEventListener(
            "click",
            applyFilters
        );

    }


    if (resetButton) {

        resetButton.addEventListener(
            "click",
            resetFilters
        );

    }

}


// =========================================================
// DATE / MONTH
// Không dùng đồng thời ngày và tháng.
// =========================================================

function setupDateMonthBehavior() {

    const dateInput =
        document.getElementById(
            "filter-date"
        );


    const monthInput =
        document.getElementById(
            "filter-month"
        );


    if (
        dateInput &&
        monthInput
    ) {

        dateInput.addEventListener(
            "change",
            function () {

                if (this.value) {

                    monthInput.value =
                        "";

                }

            }
        );


        monthInput.addEventListener(
            "change",
            function () {

                if (this.value) {

                    dateInput.value =
                        "";

                }

            }
        );

    }

}


// =========================================================
// APPLY FILTER
// =========================================================

function applyFilters() {

    const date =
        document.getElementById(
            "filter-date"
        )?.value || "";


    const month =
        document.getElementById(
            "filter-month"
        )?.value || "";


    const status =
        document.getElementById(
            "filter-status"
        )?.value || "";


    const url =
        new URL(
            window.location.href
        );


    // Xóa query cũ trước

    url.search = "";


    if (date) {

        url.searchParams.set(
            "date",
            date
        );

    }


    if (
        month &&
        !date
    ) {

        url.searchParams.set(
            "month",
            month
        );

    }


    if (status) {

        url.searchParams.set(
            "status",
            status
        );

    }


    window.location.href =
        url.toString();

}


// =========================================================
// RESET FILTER
// =========================================================

function resetFilters() {

    const cleanUrl =
        window.location.origin
        +
        window.location.pathname;


    window.location.href =
        cleanUrl;

}


// =========================================================
// ASSIGN SHIPPER
// =========================================================

function setupAssignButtons() {

    const buttons =
        document.querySelectorAll(
            ".assign-btn"
        );


    buttons.forEach(
        function (button) {

            button.addEventListener(
                "click",
                function () {

                    assignShipper(
                        this
                    );

                }
            );

        }
    );

}


// =========================================================
// ASSIGN SHIPPER REQUEST
// =========================================================

async function assignShipper(
    button
) {

    const orderId =
        button.dataset.id;


    if (!orderId) {

        showMessage(
            "Không xác định được đơn hàng.",
            "error"
        );

        return;

    }


    const select =
        document.querySelector(
            `.shipper-select[data-order="${orderId}"]`
        );


    if (!select) {

        showMessage(
            "Không tìm thấy danh sách shipper.",
            "error"
        );

        return;

    }


    const driverId =
        select.value;


    if (!driverId) {

        showMessage(
            "Vui lòng chọn shipper.",
            "warning"
        );

        select.focus();

        return;

    }


    const selectedOption =
        select.options[
            select.selectedIndex
        ];


    if (
        selectedOption &&
        selectedOption.disabled
    ) {

        showMessage(
            "Shipper này hiện không thể nhận đơn.",
            "warning"
        );

        return;

    }


    const shipperName =
        selectedOption
            ? selectedOption.textContent
                .replace(/\s+/g, " ")
                .trim()
            : "shipper";


    const confirmed =
        window.confirm(
            "Xác nhận giao đơn này cho:\n\n"
            +
            shipperName
            +
            "?"
        );


    if (!confirmed) {

        return;

    }


    const oldText =
        button.textContent;


    button.disabled =
        true;


    select.disabled =
        true;


    button.textContent =
        "Đang giao...";


    try {

        const response =
            await fetch(
                "/admin/orders/assign",
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify({

                            orderId:
                                Number(orderId),

                            driverId:
                                Number(driverId)

                        })

                }
            );


        const data =
            await readJsonResponse(
                response
            );


        if (
            !response.ok ||
            !data.success
        ) {

            throw new Error(
                data.message ||
                "Không thể giao đơn."
            );

        }


        showMessage(
            data.message ||
            "Giao đơn thành công.",
            "success"
        );


        // Reload để cập nhật đồng bộ:
        // DriverID
        // trạng thái
        // số đơn shipper
        // dropdown

        setTimeout(
            function () {

                window.location.reload();

            },
            600
        );

    }
    catch (error) {

        console.error(
            "Assign shipper error:",
            error
        );


        showMessage(
            error.message ||
            "Không thể giao đơn.",
            "error"
        );


        button.disabled =
            false;


        select.disabled =
            false;


        button.textContent =
            oldText;

    }

}


// =========================================================
// ADMIN UPDATE ORDER STATUS
// =========================================================

function setupOrderStatusButtons() {

    const buttons =
        document.querySelectorAll(
            ".update-order-btn"
        );


    buttons.forEach(
        function (button) {

            button.addEventListener(
                "click",
                function () {

                    updateOrderStatus(
                        this
                    );

                }
            );

        }
    );

}


// =========================================================
// UPDATE ORDER STATUS REQUEST
// =========================================================

async function updateOrderStatus(
    button
) {

    const orderId =
        button.dataset.id;


    if (!orderId) {

        showMessage(
            "Không xác định được đơn hàng.",
            "error"
        );

        return;

    }


    const select =
        document.getElementById(
            "status-" +
            orderId
        );


    if (!select) {

        showMessage(
            "Không tìm thấy trạng thái đơn.",
            "error"
        );

        return;

    }


    const status =
        select.value;


    if (!status) {

        showMessage(
            "Vui lòng chọn trạng thái.",
            "warning"
        );

        return;

    }


    let confirmMessage =
        "Xác nhận cập nhật đơn sang trạng thái:\n\n"
        +
        status
        +
        "?";


    if (
        status ===
        "Đã hủy"
    ) {

        confirmMessage =
            "Bạn chắc chắn muốn HỦY đơn hàng này?\n\n"
            +
            "Thao tác này sẽ kết thúc đơn và "
            +
            "gỡ shipper khỏi đơn.";

    }


    if (
        !window.confirm(
            confirmMessage
        )
    ) {

        return;

    }


    const oldText =
        button.textContent;


    button.disabled =
        true;


    select.disabled =
        true;


    button.textContent =
        "Đang lưu...";


    try {

        const response =
            await fetch(
                "/admin/orders/update/"
                +
                encodeURIComponent(
                    orderId
                ),
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify({

                            status:
                                status

                        })

                }
            );


        const data =
            await readJsonResponse(
                response
            );


        if (
            !response.ok ||
            !data.success
        ) {

            throw new Error(
                data.message ||
                "Không thể cập nhật đơn."
            );

        }


        showMessage(
            data.message ||
            "Cập nhật đơn thành công.",
            "success"
        );


        setTimeout(
            function () {

                window.location.reload();

            },
            600
        );

    }
    catch (error) {

        console.error(
            "Update order error:",
            error
        );


        showMessage(
            error.message ||
            "Không thể cập nhật trạng thái đơn.",
            "error"
        );


        button.disabled =
            false;


        select.disabled =
            false;


        button.textContent =
            oldText;

    }

}


// =========================================================
// SAFE JSON RESPONSE
// =========================================================

async function readJsonResponse(
    response
) {

    try {

        return await response.json();

    }
    catch (error) {

        console.error(
            "Invalid JSON response:",
            error
        );


        return {

            success: false,

            message:
                "Máy chủ trả về dữ liệu không hợp lệ."

        };

    }

}


// =========================================================
// TOAST MESSAGE
// =========================================================

function showMessage(
    message,
    type = "success"
) {

    // Xóa toast cũ nếu còn

    const oldToast =
        document.getElementById(
            "admin-toast"
        );


    if (oldToast) {

        oldToast.remove();

    }


    const toast =
        document.createElement(
            "div"
        );


    toast.id =
        "admin-toast";


    toast.className =
        "admin-toast "
        +
        type;


    const icon =
        getToastIcon(
            type
        );


    toast.innerHTML = `

        <div class="admin-toast-icon">
            ${icon}
        </div>

        <div class="admin-toast-content">

            <strong>
                ${getToastTitle(type)}
            </strong>

            <span>
                ${escapeHtml(message)}
            </span>

        </div>

        <button
            type="button"
            class="admin-toast-close"
        >
            ×
        </button>

    `;


    document.body.appendChild(
        toast
    );


    const closeButton =
        toast.querySelector(
            ".admin-toast-close"
        );


    if (closeButton) {

        closeButton.addEventListener(
            "click",
            function () {

                removeToast(
                    toast
                );

            }
        );

    }


    requestAnimationFrame(
        function () {

            toast.classList.add(
                "show"
            );

        }
    );


    setTimeout(
        function () {

            removeToast(
                toast
            );

        },
        4500
    );

}


// =========================================================
// REMOVE TOAST
// =========================================================

function removeToast(
    toast
) {

    if (
        !toast ||
        !toast.parentNode
    ) {

        return;

    }


    toast.classList.remove(
        "show"
    );


    setTimeout(
        function () {

            if (
                toast.parentNode
            ) {

                toast.remove();

            }

        },
        220
    );

}


// =========================================================
// TOAST ICON
// =========================================================

function getToastIcon(
    type
) {

    switch (type) {

        case "success":
            return "✓";


        case "error":
            return "!";


        case "warning":
            return "⚠";


        default:
            return "i";

    }

}


// =========================================================
// TOAST TITLE
// =========================================================

function getToastTitle(
    type
) {

    switch (type) {

        case "success":
            return "Thành công";


        case "error":
            return "Không thể thực hiện";


        case "warning":
            return "Cần kiểm tra";


        default:
            return "Thông báo";

    }

}


// =========================================================
// ESCAPE HTML
// =========================================================

function escapeHtml(
    value
) {

    const div =
        document.createElement(
            "div"
        );


    div.textContent =
        String(
            value ?? ""
        );


    return div.innerHTML;

}