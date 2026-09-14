// =========================================================
// BIẾN BẢN ĐỒ
// =========================================================

let driverMap = null;

let driverMarker = null;

let trackingTimer = null;

let currentPhone = "";


// =========================================================
// TRA CỨU ĐƠN HÀNG
// =========================================================

async function searchOrder() {

    const phoneInput =
        document.getElementById("phone");


    const phone =
        phoneInput.value.trim();


    if (phone === "") {

        alert(
            "Vui lòng nhập số điện thoại!"
        );

        return;
    }


    currentPhone = phone;


    try {

        const response =
            await fetch(
                "/api/orders/" +
                encodeURIComponent(phone)
            );


        if (!response.ok) {

            throw new Error(
                "Server trả về lỗi"
            );

        }


        const order =
            await response.json();


        if (!order) {

            showNotFound();

            stopTracking();

            return;
        }


        renderOrder(order);


        /*
         * Nếu đơn đang giao
         * thì bắt đầu theo dõi shipper.
         */

        if (
            order.status === "Đang giao"
        ) {

            startTracking();

        } else {

            stopTracking();

        }


    } catch (error) {

        console.error(
            "Lỗi tra cứu:",
            error
        );


        alert(
            "Không thể kết nối máy chủ!"
        );

    }

}


// =========================================================
// HIỆN KHÔNG TÌM THẤY
// =========================================================

function showNotFound() {

    const box =
        document.getElementById(
            "order-result"
        );


    box.innerHTML = `

        <div class="order-card not-found">

            <div class="not-found-icon">
                ❌
            </div>


            <h3>
                Không tìm thấy đơn hàng
            </h3>


            <p>
                Vui lòng kiểm tra lại số điện thoại.
            </p>

        </div>

    `;

}


// =========================================================
// XÁC ĐỊNH BƯỚC TRẠNG THÁI
// =========================================================

function getStatusStep(status) {

    const statusMap = {

        "Đã tiếp nhận": 1,

        "Đang chuẩn bị": 2,

        "Đang giao": 3,

        "Hoàn thành": 4,

        "Đã hủy": 0

    };


    return statusMap[status] ?? 1;

}


// =========================================================
// HIỂN THỊ ĐƠN HÀNG
// =========================================================

function renderOrder(order) {

    const box =
        document.getElementById(
            "order-result"
        );


    const currentStep =
        getStatusStep(
            order.status
        );


    box.innerHTML = `   


        <div class="order-card">


            <!-- HEADER ĐƠN -->

            <div class="order-heading">

                <div>

                    <p class="order-label">
                        MÃ ĐƠN HÀNG
                    </p>


                    <h2>
                        🧾 #${order.code}
                    </h2>

                </div>


                <span class="status-badge">
                    ${order.status}
                </span>

            </div>



            <!-- TRẠNG THÁI -->

            <div class="status-tracker">


                ${createStatusStep(
                    1,
                    currentStep,
                    "✓",
                    "Đã tiếp nhận",
                    "Quán đã nhận đơn"
                )}


                <div
                    class="status-line ${
                        currentStep >= 2
                            ? "completed"
                            : ""
                    }"
                ></div>


                ${createStatusStep(
                    2,
                    currentStep,
                    "🍜",
                    "Đang chuẩn bị",
                    "Món ăn đang được chuẩn bị"
                )}


                <div
                    class="status-line ${
                        currentStep >= 3
                            ? "completed"
                            : ""
                    }"
                ></div>


                ${createStatusStep(
                    3,
                    currentStep,
                    "🚚",
                    "Đang giao",
                    "Tài xế đang giao món"
                )}


                <div
                    class="status-line ${
                        currentStep >= 4
                            ? "completed"
                            : ""
                    }"
                ></div>


                ${createStatusStep(
                    4,
                    currentStep,
                    "✓",
                    "Hoàn thành",
                    "Đơn hàng đã giao"
                )}

            </div>



            <!-- THÔNG TIN GIAO HÀNG -->

            <div class="order-info">

                <h3>
                    👤 Thông tin giao hàng
                </h3>


                <div class="info-row">

                    <span>
                        Khách hàng
                    </span>


                    <strong>
                        ${escapeHTML(
                            order.name
                        )}
                    </strong>

                </div>


                <div class="info-row">

                    <span>
                        Địa chỉ
                    </span>


                    <strong>
                        ${escapeHTML(
                            order.address
                        )}
                    </strong>

                </div>


                <div class="info-row">

                    <span>
                        Trạng thái
                    </span>


                    <strong class="status-text">
                        ${escapeHTML(
                            order.status
                        )}
                    </strong>

                </div>

            </div>



            <!-- TỔNG TIỀN -->

            <div class="order-total">

                <span>
                    Tổng thanh toán
                </span>


                <strong>
                    ${formatMoney(
                        order.total
                    )}
                </strong>

            </div>



            <!-- SHIPPER -->

            ${renderDriverSection(order)}

        </div>

    `;


    /*
     * Nếu đang giao thì tạo map
     */

    if (
        order.status === "Đang giao"
    ) {

        setTimeout(
            function() {

                initDriverMap(
                    order
                );

            },
            100
        );

    }

}


// =========================================================
// TẠO STATUS
// =========================================================

function createStatusStep(
    step,
    currentStep,
    icon,
    title,
    description
) {

    let className = "";


    if (
        step < currentStep
    ) {

        className =
            "completed";

    }


    if (
        step === currentStep
    ) {

        className =
            "current";

    }


    return `

        <div
            class="status-step ${className}"
        >

            <div class="status-icon">

                ${icon}

            </div>


            <div class="status-content">

                <strong>
                    ${title}
                </strong>


                <small>
                    ${description}
                </small>

            </div>

        </div>

    `;

}


// =========================================================
// PHẦN SHIPPER
// =========================================================

function renderDriverSection(order) {

    if (order.status === "Đang giao") {

        const driverName =
            order.driver &&
            order.driver.name
                ? order.driver.name
                : "Đang tìm tài xế";


        return `
            <div class="driver active-driver">

                <div class="driver-header">

                    <div>

                        <h3>
                            🛵 Tài xế đang giao hàng
                        </h3>

                        <p>
                            ${driverName}
                        </p>

                    </div>

                    <span class="delivery-live">
                        ● Đang giao
                    </span>

                </div>

            </div>


            <div class="map-section">

                <h3>
                    📍 Vị trí tài xế
                </h3>

                <p
                    id="driver-location-text"
                >
                    Đang lấy vị trí tài xế...
                </p>


                <div
                    id="driver-map"
                    class="driver-map"
                >
                </div>

            </div>
        `;
    }


    if (order.status === "Hoàn thành") {

        return `
            <div class="driver completed-driver">

                <h3>
                    ✅ Giao hàng thành công
                </h3>

                <p>
                    Cảm ơn bạn đã đặt món
                    tại Bún Chả Việt.
                </p>

            </div>
        `;
    }


    return `
        <div class="driver">

            <h3>
                🛵 Tài xế giao hàng
            </h3>

            <p>
                Tài xế sẽ được phân công
                khi đơn hàng sẵn sàng.
            </p>

        </div>
    `;
}


// =========================================================
// KHỞI TẠO BẢN ĐỒ
// =========================================================

function initDriverMap(order) {

    const mapElement =
        document.getElementById(
            "driver-map"
        );


    if (!mapElement) {
        return;
    }


    /*
     * Nếu map đã tồn tại
     * thì xóa map cũ.
     */

    if (driverMap) {

        driverMap.remove();

        driverMap = null;

        driverMarker = null;

    }


    /*
     * Tọa độ mặc định.
     *
     * Nếu backend chưa có GPS
     * sẽ dùng Hà Nội làm vị trí ban đầu.
     */

const SHOP_LAT = 21.0338;
const SHOP_LNG = 105.8019;
const defaultLatitude =
    Number(order.latitude) || SHOP_LAT;

const defaultLongitude =
    Number(order.longitude) || SHOP_LNG;

    driverMap =
        L.map(
            "driver-map"
        ).setView(
            [
                defaultLatitude,
                defaultLongitude
            ],
            16
        );


    /*
     * OpenStreetMap
     */

    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            maxZoom: 19,

            attribution:
                "&copy; OpenStreetMap contributors"
        }
    ).addTo(
        driverMap
    );


    /*
     * Tạo icon shipper
     */

    const driverIcon =
        L.divIcon({

            className:
                "custom-driver-icon",

            html: `
                <div class="driver-marker">
                    🛵
                </div>
            `,

            iconSize: [
                58,
                70
            ],

            iconAnchor: [
                29,
                60
            ],

            popupAnchor: [
                0,
                -58
            ]

        });


    /*
     * Tạo marker
     */

    driverMarker =
        L.marker(
            [
                defaultLatitude,
                defaultLongitude
            ],
            {
                icon: driverIcon
            }
        ).addTo(
            driverMap
        );


    /*
     * Popup
     */

    const driverName =
        order.driverName ||
        "Shipper Bún Chả Việt";


    driverMarker.bindPopup(`

        <div class="driver-popup">

            <div
                class="driver-popup-name"
            >
                🛵
                ${escapeHTML(
                    driverName
                )}
            </div>


            <div
                class="driver-popup-status"
            >
                ● Đang giao hàng
            </div>

        </div>

    `);


    /*
     * Hiện marker
     */

    driverMarker.openPopup();


    /*
     * Ẩn loading
     */

    const loading =
        document.getElementById(
            "map-loading"
        );


    if (loading) {

        loading.classList.add(
            "hidden"
        );

    }


    /*
     * Nếu backend đã có tọa độ
     * thì zoom vào shipper.
     */

    if (
        order.latitude &&
        order.longitude
    ) {

        driverMap.setView(
            [
                Number(
                    order.latitude
                ),
                Number(
                    order.longitude
                )
            ],
            17
        );

    }


    /*
     * Bắt đầu lấy GPS liên tục
     */

    updateDriverLocation();

}


// =========================================================
// LẤY VỊ TRÍ SHIPPER
// =========================================================

async function updateDriverLocation() {

    if (
        !currentPhone ||
        !driverMap ||
        !driverMarker
    ) {

        return;

    }


    try {

        const response =
            await fetch(
                "/api/orders/" +
                encodeURIComponent(
                    currentPhone
                )
            );


        if (!response.ok) {

            return;

        }


        const order =
            await response.json();


        if (!order) {

            return;

        }


        /*
         * Nếu đơn không còn đang giao
         * thì dừng tracking.
         */

        if (
            order.status !==
            "Đang giao"
        ) {

            stopTracking();

            renderOrder(
                order
            );

            return;

        }


        const latitude =
            Number(
                order.latitude
            );


        const longitude =
            Number(
                order.longitude
            );


        /*
         * Chưa có GPS
         */

        if (
            !latitude ||
            !longitude
        ) {

            updateMapStatus(
                "🟡 Đang chờ GPS của tài xế..."
            );

            return;

        }


        /*
         * Vị trí mới
         */

        const newPosition =
            [
                latitude,
                longitude
            ];


        /*
         * Di chuyển marker
         */

        driverMarker.setLatLng(
            newPosition
        );


        /*
         * Bản đồ đi theo shipper
         */

        driverMap.panTo(
            newPosition,
            {
                animate: true,
                duration: 1
            }
        );


        updateMapStatus(
            "🟢 Tài xế đang trực tuyến"
        );


    } catch (error) {

        console.error(
            "Lỗi cập nhật GPS:",
            error
        );


        updateMapStatus(
            "🔴 Không thể cập nhật vị trí"
        );

    }

}


// =========================================================
// BẮT ĐẦU TRACKING
// =========================================================

function startTracking() {

    stopTracking();


    /*
     * Cập nhật ngay lập tức
     */

    updateDriverLocation();


    /*
     * Sau đó cứ 5 giây cập nhật
     */

    trackingTimer =
        setInterval(
            updateDriverLocation,
            5000
        );

}


// =========================================================
// DỪNG TRACKING
// =========================================================

function stopTracking() {

    if (trackingTimer) {

        clearInterval(
            trackingTimer
        );

        trackingTimer = null;

    }

}


// =========================================================
// STATUS MAP
// =========================================================

function updateMapStatus(
    text
) {

    const element =
        document.getElementById(
            "map-live-status"
        );


    if (!element) {
        return;
    }


    element.innerHTML =
        text;

}


// =========================================================
// FORMAT TIỀN
// =========================================================

function formatMoney(price) {

    return Number(price)
        .toLocaleString("vi-VN")
        + " ₫";

}


// =========================================================
// CHỐNG HTML INJECTION
// =========================================================

function escapeHTML(value) {

    if (
        value === null ||
        value === undefined
    ) {

        return "";

    }


    return String(value)
        .replace(
            /&/g,
            "&amp;"
        )
        .replace(
            /</g,
            "&lt;"
        )
        .replace(
            />/g,
            "&gt;"
        )
        .replace(
            /"/g,
            "&quot;"
        )
        .replace(
            /'/g,
            "&#039;"
        );

}


// =========================================================
// DỪNG TRACKING KHI RỜI TRANG
// =========================================================

window.addEventListener(
    "beforeunload",
    function() {

        stopTracking();

    }
);