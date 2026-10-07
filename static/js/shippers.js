// =========================================================
// ADMIN SHIPPER MANAGEMENT
// BUN CHA VIET
// =========================================================


document.addEventListener(
    "DOMContentLoaded",
    function () {

        setupModal();

        setupForm();

        setupEditButtons();

        setupStatusButtons();

        setupSearch();

        setupStatusFilter();

        setupPasswordToggle();

        setupToast();

    }
);


// =========================================================
// GLOBAL
// =========================================================

let editingShipperId = null;


// =========================================================
// MODAL SETUP
// =========================================================

function setupModal() {

    const modal =
        document.getElementById(
            "shipperModal"
        );


    const addButton =
        document.getElementById(
            "btnAddShipper"
        );


    const closeButton =
        document.getElementById(
            "btnClose"
        );


    if (addButton) {

        addButton.addEventListener(
            "click",
            function () {

                openAddModal();

            }
        );

    }


    if (closeButton) {

        closeButton.addEventListener(
            "click",
            function () {

                closeModal();

            }
        );

    }


    if (modal) {

        modal.addEventListener(
            "click",
            function (event) {

                if (
                    event.target === modal
                ) {

                    closeModal();

                }

            }
        );

    }


    document.addEventListener(
        "keydown",
        function (event) {

            if (
                event.key === "Escape"
            ) {

                closeModal();

            }

        }
    );

}


// =========================================================
// OPEN ADD MODAL
// =========================================================

function openAddModal() {

    editingShipperId =
        null;


    const modal =
        document.getElementById(
            "shipperModal"
        );


    const title =
        document.getElementById(
            "modalTitle"
        );


    const description =
        document.getElementById(
            "modalDescription"
        );


    const idInput =
        document.getElementById(
            "shipperId"
        );


    const fullname =
        document.getElementById(
            "fullname"
        );


    const username =
        document.getElementById(
            "username"
        );


    const password =
        document.getElementById(
            "password"
        );


    const phone =
        document.getElementById(
            "phone"
        );


    const passwordRequired =
        document.getElementById(
            "passwordRequired"
        );


    const passwordHelp =
        document.getElementById(
            "passwordHelp"
        );


    const saveButton =
        document.getElementById(
            "saveShipperBtn"
        );


    if (idInput) {
        idInput.value = "";
    }


    if (fullname) {
        fullname.value = "";
    }


    if (username) {
        username.value = "";
    }


    if (password) {
        password.value = "";

        password.required = true;

        password.type =
            "password";
    }


    if (phone) {
        phone.value = "";
    }


    if (title) {

        title.textContent =
            "Thêm shipper";

    }


    if (description) {

        description.textContent =
            "Tạo tài khoản mới cho nhân viên giao hàng.";

    }


    if (passwordRequired) {

        passwordRequired.style.display =
            "inline";

    }


    if (passwordHelp) {

        passwordHelp.textContent =
            "Mật khẩu bắt buộc khi tạo tài khoản mới.";

    }


    if (saveButton) {

        saveButton.textContent =
            "Lưu shipper";

    }


    resetPasswordToggleText();


    if (modal) {

        modal.classList.add(
            "active"
        );

        document.body.style.overflow =
            "hidden";

    }


    setTimeout(
        function () {

            fullname?.focus();

        },
        100
    );

}


// =========================================================
// OPEN EDIT MODAL
// =========================================================

function openEditModal(
    button
) {

    const modal =
        document.getElementById(
            "shipperModal"
        );


    const title =
        document.getElementById(
            "modalTitle"
        );


    const description =
        document.getElementById(
            "modalDescription"
        );


    const idInput =
        document.getElementById(
            "shipperId"
        );


    const fullname =
        document.getElementById(
            "fullname"
        );


    const username =
        document.getElementById(
            "username"
        );


    const password =
        document.getElementById(
            "password"
        );


    const phone =
        document.getElementById(
            "phone"
        );


    const passwordRequired =
        document.getElementById(
            "passwordRequired"
        );


    const passwordHelp =
        document.getElementById(
            "passwordHelp"
        );


    const saveButton =
        document.getElementById(
            "saveShipperBtn"
        );


    editingShipperId =
        button.dataset.id;


    if (idInput) {

        idInput.value =
            editingShipperId || "";

    }


    if (fullname) {

        fullname.value =
            button.dataset.fullname || "";

    }


    if (username) {

        username.value =
            button.dataset.username || "";

    }


    if (phone) {

        phone.value =
            button.dataset.phone || "";

    }


    if (password) {

        password.value = "";

        password.required =
            false;

        password.type =
            "password";

    }


    if (title) {

        title.textContent =
            "Cập nhật shipper";

    }


    if (description) {

        description.textContent =
            "Chỉnh sửa thông tin tài khoản giao hàng.";

    }


    if (passwordRequired) {

        passwordRequired.style.display =
            "none";

    }


    if (passwordHelp) {

        passwordHelp.textContent =
            "Để trống nếu không muốn đổi mật khẩu.";

    }


    if (saveButton) {

        saveButton.textContent =
            "Lưu thay đổi";

    }


    resetPasswordToggleText();


    if (modal) {

        modal.classList.add(
            "active"
        );

        document.body.style.overflow =
            "hidden";

    }


    setTimeout(
        function () {

            fullname?.focus();

        },
        100
    );

}


// =========================================================
// CLOSE MODAL
// =========================================================

function closeModal() {

    const modal =
        document.getElementById(
            "shipperModal"
        );


    if (!modal) {
        return;
    }


    modal.classList.remove(
        "active"
    );


    document.body.style.overflow =
        "";


    editingShipperId =
        null;

}


// =========================================================
// EDIT BUTTONS
// =========================================================

function setupEditButtons() {

    const buttons =
        document.querySelectorAll(
            ".edit-btn"
        );


    buttons.forEach(
        function (button) {

            button.addEventListener(
                "click",
                function () {

                    openEditModal(
                        this
                    );

                }
            );

        }
    );

}


// =========================================================
// FORM SETUP
// =========================================================

function setupForm() {

    const form =
        document.getElementById(
            "shipperForm"
        );


    if (!form) {
        return;
    }


    form.addEventListener(
        "submit",
        function (event) {

            event.preventDefault();

            saveShipper();

        }
    );

}


// =========================================================
// SAVE SHIPPER
// =========================================================

async function saveShipper() {

    const fullname =
        document.getElementById(
            "fullname"
        )?.value.trim() || "";


    const username =
        document.getElementById(
            "username"
        )?.value.trim() || "";


    const password =
        document.getElementById(
            "password"
        )?.value || "";


    const phone =
        document.getElementById(
            "phone"
        )?.value.trim() || "";


    const saveButton =
        document.getElementById(
            "saveShipperBtn"
        );


    // =====================================================
    // VALIDATION
    // =====================================================

    if (!fullname) {

        showToast(
            "warning",
            "Thiếu thông tin",
            "Vui lòng nhập họ và tên shipper."
        );

        document.getElementById(
            "fullname"
        )?.focus();

        return;

    }


    if (!username) {

        showToast(
            "warning",
            "Thiếu thông tin",
            "Vui lòng nhập tên đăng nhập."
        );

        document.getElementById(
            "username"
        )?.focus();

        return;

    }


    if (
        !editingShipperId &&
        !password
    ) {

        showToast(
            "warning",
            "Thiếu mật khẩu",
            "Mật khẩu bắt buộc khi tạo shipper mới."
        );

        document.getElementById(
            "password"
        )?.focus();

        return;

    }


    if (
        phone &&
        !isValidPhone(phone)
    ) {

        showToast(
            "warning",
            "Số điện thoại chưa hợp lệ",
            "Số điện thoại chỉ nên chứa từ 9 đến 15 chữ số."
        );

        document.getElementById(
            "phone"
        )?.focus();

        return;

    }


    // =====================================================
    // REQUEST
    // =====================================================

    let endpoint =
        "/admin/shippers/add";


    if (editingShipperId) {

        endpoint =
            "/admin/shippers/update/"
            +
            encodeURIComponent(
                editingShipperId
            );

    }


    const payload = {

        fullname:
            fullname,

        username:
            username,

        password:
            password,

        phone:
            phone

    };


    const oldText =
        saveButton?.textContent || "";


    if (saveButton) {

        saveButton.disabled =
            true;

        saveButton.textContent =
            editingShipperId
                ? "Đang lưu..."
                : "Đang tạo...";

    }


    try {

        const response =
            await fetch(
                endpoint,
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify(
                            payload
                        )

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
                "Không thể lưu shipper."
            );

        }


        closeModal();


        showToast(
            "success",
            "Thành công",
            data.message ||
            (
                editingShipperId
                    ? "Đã cập nhật shipper."
                    : "Đã thêm shipper."
            )
        );


        setTimeout(
            function () {

                window.location.reload();

            },
            650
        );

    }
    catch (error) {

        console.error(
            "Save shipper error:",
            error
        );


        showToast(
            "error",
            "Không thể lưu",
            error.message ||
            "Đã xảy ra lỗi khi lưu shipper."
        );


        if (saveButton) {

            saveButton.disabled =
                false;

            saveButton.textContent =
                oldText;

        }

    }

}


// =========================================================
// LOCK / UNLOCK BUTTONS
// =========================================================

function setupStatusButtons() {

    const lockButtons =
        document.querySelectorAll(
            ".lock-btn"
        );


    const unlockButtons =
        document.querySelectorAll(
            ".unlock-btn"
        );


    lockButtons.forEach(
        function (button) {

            button.addEventListener(
                "click",
                function () {

                    handleLock(
                        this
                    );

                }
            );

        }
    );


    unlockButtons.forEach(
        function (button) {

            button.addEventListener(
                "click",
                function () {

                    handleUnlock(
                        this
                    );

                }
            );

        }
    );

}


// =========================================================
// LOCK
// =========================================================

async function handleLock(
    button
) {

    const id =
        button.dataset.id;


    const name =
        button.dataset.name ||
        "shipper";


    const activeOrders =
        Number(
            button.dataset.activeOrders
            || 0
        );


    if (!id) {

        showToast(
            "error",
            "Không thể thực hiện",
            "Không xác định được shipper."
        );

        return;

    }


    if (activeOrders > 0) {

        showToast(
            "warning",
            "Không thể khóa",
            `${name} còn ${activeOrders} đơn đang xử lý.`
        );

        return;

    }


    const confirmed =
        window.confirm(
            "Xác nhận khóa tài khoản:\n\n"
            +
            name
            +
            "?\n\n"
            +
            "Shipper sẽ không thể đăng nhập "
            +
            "và trạng thái nhận đơn sẽ được tắt."
        );


    if (!confirmed) {
        return;
    }


    await changeShipperStatus(
        button,
        id,
        0,
        "Đang khóa..."
    );

}


// =========================================================
// UNLOCK
// =========================================================

async function handleUnlock(
    button
) {

    const id =
        button.dataset.id;


    const name =
        button.dataset.name ||
        "shipper";


    if (!id) {

        showToast(
            "error",
            "Không thể thực hiện",
            "Không xác định được shipper."
        );

        return;

    }


    const confirmed =
        window.confirm(
            "Xác nhận mở khóa tài khoản:\n\n"
            +
            name
            +
            "?\n\n"
            +
            "Sau khi mở khóa, shipper vẫn ở trạng thái nghỉ ca "
            +
            "và phải tự bật nhận đơn."
        );


    if (!confirmed) {
        return;
    }


    await changeShipperStatus(
        button,
        id,
        1,
        "Đang mở..."
    );

}


// =========================================================
// STATUS REQUEST
// =========================================================

async function changeShipperStatus(
    button,
    id,
    isActive,
    loadingText
) {

    const oldText =
        button.textContent;


    button.disabled =
        true;


    button.textContent =
        loadingText;


    try {

        const response =
            await fetch(
                "/admin/shippers/status/"
                +
                encodeURIComponent(
                    id
                ),
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify({

                            isActive:
                                isActive

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
                "Không thể cập nhật trạng thái shipper."
            );

        }


        showToast(
            "success",
            "Đã cập nhật",
            data.message ||
            "Cập nhật trạng thái shipper thành công."
        );


        setTimeout(
            function () {

                window.location.reload();

            },
            650
        );

    }
    catch (error) {

        console.error(
            "Update shipper status error:",
            error
        );


        showToast(
            "error",
            "Không thể cập nhật",
            error.message ||
            "Đã xảy ra lỗi."
        );


        button.disabled =
            false;


        button.textContent =
            oldText;

    }

}


// =========================================================
// SEARCH
// =========================================================

function setupSearch() {

    const search =
        document.getElementById(
            "shipperSearch"
        );


    if (!search) {
        return;
    }


    search.addEventListener(
        "input",
        function () {

            filterShippers();

        }
    );

}


// =========================================================
// STATUS FILTER
// =========================================================

function setupStatusFilter() {

    const select =
        document.getElementById(
            "shipperStatusFilter"
        );


    if (!select) {
        return;
    }


    select.addEventListener(
        "change",
        function () {

            filterShippers();

        }
    );

}


// =========================================================
// FILTER SHIPPERS
// =========================================================

function filterShippers() {

    const search =
        normalizeText(
            document.getElementById(
                "shipperSearch"
            )?.value || ""
        );


    const status =
        document.getElementById(
            "shipperStatusFilter"
        )?.value || "";


    const rows =
        document.querySelectorAll(
            ".shipper-row"
        );


    let visibleCount = 0;


    rows.forEach(
        function (row) {

            const searchableText =
                normalizeText(
                    row.dataset.search || ""
                );


            const rowStatus =
                row.dataset.status || "";


            const matchSearch =
                !search ||
                searchableText.includes(
                    search
                );


            const matchStatus =
                !status ||
                rowStatus === status;


            const visible =
                matchSearch &&
                matchStatus;


            row.style.display =
                visible
                    ? ""
                    : "none";


            if (visible) {

                visibleCount++;

            }

        }
    );


    const emptyState =
        document.getElementById(
            "shipperSearchEmpty"
        );


    if (emptyState) {

        emptyState.style.display =
            visibleCount === 0
                ? "flex"
                : "none";

    }

}


// =========================================================
// NORMALIZE SEARCH TEXT
// =========================================================

function normalizeText(
    value
) {

    return String(
        value || ""
    )
        .normalize("NFD")
        .replace(
            /[\u0300-\u036f]/g,
            ""
        )
        .toLowerCase()
        .trim();

}


// =========================================================
// PASSWORD TOGGLE
// =========================================================

function setupPasswordToggle() {

    const button =
        document.getElementById(
            "togglePassword"
        );


    const input =
        document.getElementById(
            "password"
        );


    if (
        !button ||
        !input
    ) {

        return;

    }


    button.addEventListener(
        "click",
        function () {

            if (
                input.type === "password"
            ) {

                input.type =
                    "text";

                button.textContent =
                    "Ẩn";

            }
            else {

                input.type =
                    "password";

                button.textContent =
                    "Hiện";

            }

        }
    );

}


// =========================================================
// RESET PASSWORD TOGGLE
// =========================================================

function resetPasswordToggleText() {

    const button =
        document.getElementById(
            "togglePassword"
        );


    if (button) {

        button.textContent =
            "Hiện";

    }

}


// =========================================================
// PHONE VALIDATION
// =========================================================

function isValidPhone(
    value
) {

    const normalized =
        value.replace(
            /[\s.\-()]/g,
            ""
        );


    return /^\+?\d{9,15}$/.test(
        normalized
    );

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
// TOAST SETUP
// =========================================================

function setupToast() {

    const closeButton =
        document.getElementById(
            "shipperToastClose"
        );


    if (!closeButton) {
        return;
    }


    closeButton.addEventListener(
        "click",
        function () {

            hideToast();

        }
    );

}


// =========================================================
// SHOW TOAST
// =========================================================

function showToast(
    type,
    title,
    message
) {

    const toast =
        document.getElementById(
            "shipperToast"
        );


    const icon =
        toast?.querySelector(
            ".shipper-toast-icon"
        );


    const titleElement =
        document.getElementById(
            "shipperToastTitle"
        );


    const messageElement =
        document.getElementById(
            "shipperToastMessage"
        );


    if (!toast) {

        window.alert(
            message
        );

        return;

    }


    toast.classList.remove(
        "success",
        "error",
        "warning"
    );


    toast.classList.add(
        type
    );


    if (icon) {

        icon.textContent =
            getToastIcon(
                type
            );

    }


    if (titleElement) {

        titleElement.textContent =
            title;

    }


    if (messageElement) {

        messageElement.textContent =
            message;

    }


    toast.classList.add(
        "show"
    );


    clearTimeout(
        toast._hideTimer
    );


    toast._hideTimer =
        setTimeout(
            function () {

                hideToast();

            },
            4500
        );

}


// =========================================================
// HIDE TOAST
// =========================================================

function hideToast() {

    const toast =
        document.getElementById(
            "shipperToast"
        );


    if (!toast) {
        return;
    }


    toast.classList.remove(
        "show"
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

        case "warning":
            return "⚠";

        case "error":
            return "!";

        default:
            return "i";

    }

}