// =========================================================
// GLOBAL STATE
// =========================================================

let selectedFailedOrderId = null;
let selectedFailedOrderCode = null;
let locationWatcherId = null;


// =========================================================
// INIT
// =========================================================

document.addEventListener(
    "DOMContentLoaded",
    function () {

        setupSidebarNavigation();

        setupSectionLinks();

        setupWorkButton();

        setupOrderActions();

        setupFailedDeliveryModal();

        buildFilteredOrderSections();

        updateActiveOrderCount();

        setupGPS();
    }
);


// =========================================================
// SIDEBAR NAVIGATION
// =========================================================

function setupSidebarNavigation() {

    const menuItems =
        document.querySelectorAll(
            ".menu-item[data-target]"
        );

    menuItems.forEach(
        function (item) {

            item.addEventListener(
                "click",
                function () {

                    const target =
                        this.dataset.target;

                    openSection(target);
                }
            );
        }
    );
}


function openSection(sectionId) {

    if (!sectionId) {
        return;
    }


    const menuItems =
        document.querySelectorAll(
            ".menu-item[data-target]"
        );


    const sections =
        document.querySelectorAll(
            ".content-section"
        );


    menuItems.forEach(
        function (item) {

            item.classList.remove(
                "active"
            );


            if (
                item.dataset.target ===
                sectionId
            ) {

                item.classList.add(
                    "active"
                );
            }
        }
    );


    sections.forEach(
        function (section) {

            section.classList.remove(
                "active"
            );
        }
    );


    const targetSection =
        document.getElementById(
            sectionId
        );


    if (targetSection) {

        targetSection.classList.add(
            "active"
        );
    }


    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });
}


// =========================================================
// LINKS INSIDE CONTENT
// =========================================================

function setupSectionLinks() {

    const buttons =
        document.querySelectorAll(
            "[data-open-section]"
        );


    buttons.forEach(
        function (button) {

            button.addEventListener(
                "click",
                function () {

                    openSection(
                        this.dataset.openSection
                    );
                }
            );
        }
    );
}


// =========================================================
// BUILD FILTERED SECTIONS
// =========================================================

function buildFilteredOrderSections() {

    const sourceCards =
        document.querySelectorAll(
            "#overview .order-card"
        );


    const activeContainer =
        document.querySelector(
            '[data-filter-section="active"]'
        );


    const completedContainer =
        document.querySelector(
            '[data-filter-section="completed"]'
        );


    const failedContainer =
        document.querySelector(
            '[data-filter-section="failed"]'
        );


    if (activeContainer) {
        activeContainer.innerHTML = "";
    }

    if (completedContainer) {
        completedContainer.innerHTML = "";
    }

    if (failedContainer) {
        failedContainer.innerHTML = "";
    }


    let activeCount = 0;
    let completedCount = 0;
    let failedCount = 0;


    sourceCards.forEach(
        function (card) {

            const status =
                (
                    card.dataset.orderStatus ||
                    ""
                ).trim();


            if (
                isActiveOrderStatus(status)
            ) {

                activeCount++;

                appendCardClone(
                    activeContainer,
                    card
                );
            }


            if (
                status ===
                "Hoàn thành"
            ) {

                completedCount++;

                appendCardClone(
                    completedContainer,
                    card
                );
            }


            if (
                isFailedOrderStatus(status)
            ) {

                failedCount++;

                appendCardClone(
                    failedContainer,
                    card
                );
            }
        }
    );


    if (
        activeContainer &&
        activeCount === 0
    ) {

        activeContainer.innerHTML =
            createEmptyState(
                "🛵",
                "Không có đơn đang xử lý",
                "Bạn hiện không có đơn nào cần giao."
            );
    }


    if (
        completedContainer &&
        completedCount === 0
    ) {

        completedContainer.innerHTML =
            createEmptyState(
                "✓",
                "Chưa có đơn hoàn thành",
                "Các đơn giao thành công sẽ xuất hiện tại đây."
            );
    }


    if (
        failedContainer &&
        failedCount === 0
    ) {

        failedContainer.innerHTML =
            createEmptyState(
                "📦",
                "Không có đơn giao thất bại",
                "Hiện chưa có đơn nào được ghi nhận là không giao được."
            );
    }
}


function appendCardClone(
    container,
    card
) {

    if (!container) {
        return;
    }


    const clonedCard =
        card.cloneNode(true);


    container.appendChild(
        clonedCard
    );
}


function createEmptyState(
    icon,
    title,
    description
) {

    return `
        <div class="empty-state">

            <div class="empty-icon">
                ${icon}
            </div>

            <h3>
                ${title}
            </h3>

            <p>
                ${description}
            </p>

        </div>
    `;
}


// =========================================================
// STATUS HELPERS
// =========================================================

function isActiveOrderStatus(status) {

    return [
        "Đã giao shipper",
        "Đang chuẩn bị",
        "Đang giao"
    ].includes(status);
}


function isFailedOrderStatus(status) {

    return [
        "Không giao được",
        "Đã hủy"
    ].includes(status);
}


// =========================================================
// ACTIVE ORDER COUNT
// =========================================================

function updateActiveOrderCount() {

    const cards =
        document.querySelectorAll(
            "#overview .order-card"
        );


    let count = 0;


    cards.forEach(
        function (card) {

            const status =
                (
                    card.dataset.orderStatus ||
                    ""
                ).trim();


            if (
                isActiveOrderStatus(status)
            ) {

                count++;
            }
        }
    );


    const menuCount =
        document.getElementById(
            "activeOrderCount"
        );


    if (menuCount) {

        menuCount.textContent =
            count;
    }


    const statTotals =
        document.querySelectorAll(
            ".active-orders-total"
        );


    statTotals.forEach(
        function (element) {

            element.textContent =
                count;
        }
    );
}


// =========================================================
// WORK SHIFT
// =========================================================

function setupWorkButton() {

    const button =
        document.getElementById(
            "toggleWorkBtn"
        );


    if (!button) {
        return;
    }


    button.addEventListener(
        "click",
        async function () {

            if (button.disabled) {
                return;
            }


            button.disabled = true;


            const oldText =
                button.textContent;


            button.textContent =
                "Đang xử lý...";


            try {

                const response =
                    await fetch(
                        "/shipper/toggle-work",
                        {
                            method: "POST"
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

                    alert(
                        data.message ||
                        "Không thể thay đổi trạng thái ca."
                    );

                    button.disabled = false;

                    button.textContent =
                        oldText;

                    return;
                }


                window.location.reload();

            }
            catch (error) {

                console.error(
                    "Toggle work error:",
                    error
                );


                alert(
                    "Không thể kết nối tới máy chủ."
                );


                button.disabled = false;

                button.textContent =
                    oldText;
            }
        }
    );
}


// =========================================================
// ORDER ACTIONS
// =========================================================

function setupOrderActions() {

    document.addEventListener(
        "click",
        async function (event) {

            const statusButton =
                event.target.closest(
                    ".status-btn"
                );


            if (statusButton) {

                event.preventDefault();


                await updateOrderStatus(
                    statusButton
                );


                return;
            }


            const failedButton =
                event.target.closest(
                    ".failed-order-btn"
                );


            if (failedButton) {

                event.preventDefault();


                openFailedDeliveryModal(
                    failedButton
                );
            }
        }
    );
}


// =========================================================
// UPDATE ORDER STATUS
// =========================================================

async function updateOrderStatus(
    button
) {

    const orderId =
        button.dataset.id;


    const newStatus =
        button.dataset.status;


    if (
        !orderId ||
        !newStatus
    ) {

        return;
    }


    let confirmMessage = null;


    if (
        newStatus ===
        "Đang chuẩn bị"
    ) {

        confirmMessage =
            "Xác nhận bạn đã nhận món cho đơn này?";
    }


    if (
        newStatus ===
        "Đang giao"
    ) {

        confirmMessage =
            "Xác nhận bắt đầu giao đơn hàng?";
    }


    if (
        newStatus ===
        "Hoàn thành"
    ) {

        confirmMessage =
            "Xác nhận khách đã nhận hàng và bạn đã thu tiền?";
    }


    if (
        confirmMessage &&
        !window.confirm(confirmMessage)
    ) {

        return;
    }


    button.disabled = true;


    const oldContent =
        button.innerHTML;


    button.innerHTML =
        "Đang cập nhật...";


    try {

        const response =
            await fetch(
                "/shipper/update/" +
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
                                newStatus
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

            alert(
                data.message ||
                "Không thể cập nhật trạng thái đơn."
            );


            button.disabled = false;

            button.innerHTML =
                oldContent;

            return;
        }


        window.location.reload();

    }
    catch (error) {

        console.error(
            "Update order error:",
            error
        );


        alert(
            "Không thể kết nối tới máy chủ."
        );


        button.disabled = false;

        button.innerHTML =
            oldContent;
    }
}


// =========================================================
// FAILED DELIVERY MODAL
// =========================================================

function setupFailedDeliveryModal() {

    const closeButton =
        document.getElementById(
            "closeFailedModal"
        );


    const cancelButton =
        document.getElementById(
            "cancelFailedModal"
        );


    const confirmButton =
        document.getElementById(
            "confirmFailedDelivery"
        );


    const modal =
        document.getElementById(
            "failedDeliveryModal"
        );


    if (closeButton) {

        closeButton.addEventListener(
            "click",
            closeFailedDeliveryModal
        );
    }


    if (cancelButton) {

        cancelButton.addEventListener(
            "click",
            closeFailedDeliveryModal
        );
    }


    if (confirmButton) {

        confirmButton.addEventListener(
            "click",
            submitFailedDelivery
        );
    }


    if (modal) {

        modal.addEventListener(
            "click",
            function (event) {

                if (
                    event.target === modal
                ) {

                    closeFailedDeliveryModal();
                }
            }
        );
    }


    document.addEventListener(
        "keydown",
        function (event) {

            if (
                event.key ===
                "Escape"
            ) {

                closeFailedDeliveryModal();
            }
        }
    );
}


// =========================================================
// OPEN FAILED MODAL
// =========================================================

function openFailedDeliveryModal(
    button
) {

    const modal =
        document.getElementById(
            "failedDeliveryModal"
        );


    if (!modal) {
        return;
    }


    selectedFailedOrderId =
        button.dataset.id;


    selectedFailedOrderCode =
        button.dataset.code;


    const codeElement =
        document.getElementById(
            "failedOrderCode"
        );


    if (codeElement) {

        codeElement.textContent =
            "Đơn #" +
            (
                selectedFailedOrderCode ||
                selectedFailedOrderId
            );
    }


    const reason =
        document.getElementById(
            "failedReason"
        );


    const note =
        document.getElementById(
            "failedNote"
        );


    if (reason) {
        reason.value = "";
    }


    if (note) {
        note.value = "";
    }


    modal.classList.add(
        "show"
    );


    document.body.style.overflow =
        "hidden";
}


// =========================================================
// CLOSE FAILED MODAL
// =========================================================

function closeFailedDeliveryModal() {

    const modal =
        document.getElementById(
            "failedDeliveryModal"
        );


    if (!modal) {
        return;
    }


    modal.classList.remove(
        "show"
    );


    document.body.style.overflow =
        "";


    selectedFailedOrderId =
        null;


    selectedFailedOrderCode =
        null;
}


// =========================================================
// SUBMIT FAILED DELIVERY
// =========================================================

async function submitFailedDelivery() {

    if (!selectedFailedOrderId) {

        return;
    }


    const reasonElement =
        document.getElementById(
            "failedReason"
        );


    const noteElement =
        document.getElementById(
            "failedNote"
        );


    const confirmButton =
        document.getElementById(
            "confirmFailedDelivery"
        );


    const reason =
        reasonElement
            ? reasonElement.value.trim()
            : "";


    const note =
        noteElement
            ? noteElement.value.trim()
            : "";


    if (!reason) {

        alert(
            "Bạn cần chọn lý do không giao được."
        );


        if (reasonElement) {
            reasonElement.focus();
        }


        return;
    }


    if (
        !window.confirm(
            "Xác nhận đơn hàng này không thể giao?"
        )
    ) {

        return;
    }


    if (confirmButton) {

        confirmButton.disabled =
            true;

        confirmButton.textContent =
            "Đang lưu...";
    }


    try {

        const response =
            await fetch(
                "/shipper/cancel/" +
                encodeURIComponent(
                    selectedFailedOrderId
                ),
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({
                            reason: reason,
                            note: note
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

            alert(
                data.message ||
                "Không thể ghi nhận đơn giao thất bại."
            );


            if (confirmButton) {

                confirmButton.disabled =
                    false;

                confirmButton.textContent =
                    "Xác nhận không giao được";
            }


            return;
        }


        window.location.reload();

    }
    catch (error) {

        console.error(
            "Failed delivery error:",
            error
        );


        alert(
            "Backend chưa xử lý API không giao được hoặc server đang lỗi."
        );


        if (confirmButton) {

            confirmButton.disabled =
                false;

            confirmButton.textContent =
                "Xác nhận không giao được";
        }
    }
}


// =========================================================
// GPS
// =========================================================

function setupGPS() {

    const isWorking =
        document.body.dataset.working ===
        "1";


    if (!isWorking) {

        console.log(
            "Shipper đang nghỉ ca. GPS không được gửi."
        );

        return;
    }


    if (
        !navigator.geolocation
    ) {

        console.warn(
            "Trình duyệt không hỗ trợ GPS."
        );

        return;
    }


    locationWatcherId =
        navigator.geolocation.watchPosition(

            sendLocation,

            handleLocationError,

            {
                enableHighAccuracy: true,

                maximumAge: 10000,

                timeout: 15000
            }
        );
}


// =========================================================
// SEND GPS
// =========================================================

async function sendLocation(
    position
) {

    const latitude =
        position.coords.latitude;


    const longitude =
        position.coords.longitude;


    try {

        const response =
            await fetch(
                "/shipper/location",
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({
                            latitude:
                                latitude,

                            longitude:
                                longitude
                        })
                }
            );


        if (!response.ok) {

            console.warn(
                "Server từ chối cập nhật GPS."
            );


            return;
        }


        const data =
            await readJsonResponse(
                response
            );


        if (!data.success) {

            console.warn(
                data.message ||
                "Không thể cập nhật GPS."
            );
        }

    }
    catch (error) {

        console.error(
            "GPS request error:",
            error
        );
    }
}


// =========================================================
// GPS ERROR
// =========================================================

function handleLocationError(
    error
) {

    switch (
        error.code
    ) {

        case error.PERMISSION_DENIED:

            console.warn(
                "Người dùng chưa cấp quyền vị trí."
            );

            break;


        case error.POSITION_UNAVAILABLE:

            console.warn(
                "Không xác định được vị trí."
            );

            break;


        case error.TIMEOUT:

            console.warn(
                "Lấy vị trí quá thời gian."
            );

            break;


        default:

            console.warn(
                "Lỗi GPS:",
                error.message
            );
    }
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
            "Response không phải JSON:",
            error
        );


        return {
            success: false,
            message:
                "Server trả về dữ liệu không hợp lệ."
        };
    }
}