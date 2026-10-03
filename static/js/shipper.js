let selectedCancelOrderId = null;

let locationWatcherId = null;



document.addEventListener(
    "DOMContentLoaded",
    function () {

        setupNavigation();

        setupWorkButton();

        setupOrderButtons();

        setupCancelModal();

        setupStatistics();

        setupGPS();

    }
);



// =========================================================
// SIDEBAR
// =========================================================

function setupNavigation() {

    const navigationButtons =
        document.querySelectorAll(
            ".nav-item[data-section]"
        );


    const sections =
        document.querySelectorAll(
            ".page-section"
        );


    navigationButtons.forEach(
        button => {

            button.addEventListener(
                "click",
                function () {

                    const sectionName =
                        this.dataset.section;


                    navigationButtons
                        .forEach(item =>
                            item.classList.remove(
                                "active"
                            )
                        );


                    this.classList.add(
                        "active"
                    );


                    sections.forEach(
                        section => {

                            section.classList.remove(
                                "active"
                            );

                        }
                    );


                    const target =
                        document.getElementById(
                            "section-" +
                            sectionName
                        );


                    if (target) {

                        target.classList.add(
                            "active"
                        );

                    }

                }
            );

        }
    );

}



// =========================================================
// WORKING STATUS
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

            button.disabled = true;


            try {

                const response =
                    await fetch(
                        "/shipper/toggle-work",
                        {
                            method: "POST"
                        }
                    );


                const data =
                    await response.json();


                if (!data.success) {

                    alert(
                        data.message ||
                        "Không thể thay đổi trạng thái."
                    );

                    button.disabled = false;

                    return;

                }


                location.reload();

            }
            catch (error) {

                console.error(error);

                alert(
                    "Không thể kết nối đến máy chủ."
                );

                button.disabled = false;

            }

        }
    );

}



// =========================================================
// ORDER STATUS
// =========================================================

function setupOrderButtons() {

    const buttons =
        document.querySelectorAll(
            ".status-btn"
        );


    buttons.forEach(
        button => {

            button.addEventListener(
                "click",
                async function () {

                    const orderId =
                        this.dataset.id;


                    const status =
                        this.dataset.status;


                    if (!orderId || !status) {

                        return;

                    }


                    this.disabled = true;


                    try {

                        const response =
                            await fetch(
                                "/shipper/update/" +
                                orderId,
                                {

                                    method: "POST",

                                    headers: {

                                        "Content-Type":
                                            "application/json"

                                    },

                                    body:
                                        JSON.stringify(
                                            {
                                                status: status
                                            }
                                        )

                                }
                            );


                        const data =
                            await response.json();


                        if (!data.success) {

                            alert(
                                data.message ||
                                "Không thể cập nhật đơn."
                            );

                            this.disabled = false;

                            return;

                        }


                        location.reload();

                    }
                    catch (error) {

                        console.error(error);

                        alert(
                            "Lỗi kết nối server."
                        );

                        this.disabled = false;

                    }

                }
            );

        }
    );

}



// =========================================================
// CANCEL DELIVERY MODAL
// =========================================================

function setupCancelModal() {

    const modal =
        document.getElementById(
            "cancelModal"
        );


    const buttons =
        document.querySelectorAll(
            ".cancel-order-btn"
        );


    const closeButton =
        document.getElementById(
            "closeCancelModal"
        );


    const backButton =
        document.getElementById(
            "cancelModalBack"
        );


    const confirmButton =
        document.getElementById(
            "confirmCancelOrder"
        );


    buttons.forEach(
        button => {

            button.addEventListener(
                "click",
                function () {

                    selectedCancelOrderId =
                        this.dataset.id;


                    const orderCode =
                        this.dataset.code;


                    document
                        .getElementById(
                            "cancelOrderCode"
                        )
                        .textContent =
                        "Đơn #" + orderCode;


                    modal.classList.add(
                        "show"
                    );

                }
            );

        }
    );


    function closeModal() {

        modal.classList.remove(
            "show"
        );


        selectedCancelOrderId =
            null;


        document
            .getElementById(
                "cancelReason"
            )
            .value = "";


        document
            .getElementById(
                "cancelNote"
            )
            .value = "";

    }


    if (closeButton) {

        closeButton.addEventListener(
            "click",
            closeModal
        );

    }


    if (backButton) {

        backButton.addEventListener(
            "click",
            closeModal
        );

    }


    modal.addEventListener(
        "click",
        function (event) {

            if (event.target === modal) {

                closeModal();

            }

        }
    );


    if (confirmButton) {

        confirmButton.addEventListener(
            "click",
            submitCancelOrder
        );

    }

}



// =========================================================
// SUBMIT CANCEL ORDER
// =========================================================

async function submitCancelOrder() {

    if (!selectedCancelOrderId) {

        return;

    }


    const reason =
        document.getElementById(
            "cancelReason"
        ).value;


    const note =
        document.getElementById(
            "cancelNote"
        ).value.trim();


    if (!reason) {

        alert(
            "Bạn cần chọn lý do không giao được."
        );

        return;

    }


    const button =
        document.getElementById(
            "confirmCancelOrder"
        );


    button.disabled = true;


    try {

        const response =
            await fetch(
                "/shipper/cancel/" +
                selectedCancelOrderId,
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body:
                        JSON.stringify(
                            {

                                reason: reason,

                                note: note

                            }
                        )

                }
            );


        const data =
            await response.json();


        if (!data.success) {

            alert(
                data.message ||
                "Không thể cập nhật đơn."
            );

            button.disabled = false;

            return;

        }


        location.reload();

    }
    catch (error) {

        console.error(error);


        alert(
            "Chức năng này cần nối API hủy đơn ở backend."
        );


        button.disabled = false;

    }

}



// =========================================================
// STATISTICS BY DATE
// =========================================================

function setupStatistics() {

    const button =
        document.getElementById(
            "viewStatisticsBtn"
        );


    const dateInput =
        document.getElementById(
            "statsDate"
        );


    if (!button || !dateInput) {

        return;

    }


    button.addEventListener(
        "click",
        function () {

            const selectedDate =
                dateInput.value;


            if (!selectedDate) {

                alert(
                    "Hãy chọn ngày cần xem."
                );

                return;

            }


            const url =
                new URL(
                    window.location.href
                );


            url.searchParams.set(
                "date",
                selectedDate
            );


            url.searchParams.set(
                "section",
                "statistics"
            );


            window.location.href =
                url.toString();

        }
    );


    const params =
        new URLSearchParams(
            window.location.search
        );


    if (
        params.get("section") ===
        "statistics"
    ) {

        const statisticsButton =
            document.querySelector(
                '[data-section="statistics"]'
            );


        if (statisticsButton) {

            statisticsButton.click();

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
            "Shipper đang nghỉ ca, GPS không gửi."
        );

        return;

    }


    if (!navigator.geolocation) {

        console.warn(
            "Thiết bị không hỗ trợ GPS."
        );

        return;

    }


    locationWatcherId =
        navigator.geolocation.watchPosition(

            sendLocation,

            locationError,

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
                        JSON.stringify(
                            {

                                latitude:
                                    latitude,

                                longitude:
                                    longitude

                            }
                        )

                }
            );


        const data =
            await response.json();


        if (!data.success) {

            console.warn(
                data.message ||
                "GPS không được cập nhật."
            );

        }

    }
    catch (error) {

        console.error(
            "Lỗi gửi GPS:",
            error
        );

    }

}



// =========================================================
// GPS ERROR
// =========================================================

function locationError(
    error
) {

    console.warn(
        "Không lấy được vị trí GPS:",
        error.message
    );

}