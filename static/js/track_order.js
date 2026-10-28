let currentPhone = "";

let currentOrders = [];

let trackingTimer = null;


const trackingMaps =
    new Map();


// =========================================================
// INIT
// =========================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        const phoneInput =
            document.getElementById(
                "phone"
            );


        phoneInput?.addEventListener(
            "keydown",
            (event) => {

                if (
                    event.key ===
                    "Enter"
                ) {

                    event.preventDefault();

                    searchOrder();

                }

            }
        );


        const lastOrderPhone =
            localStorage.getItem(
                "lastOrderPhone"
            )
            ||
            "";


        const newOrderCode =
            localStorage.getItem(
                "orderCode"
            )
            ||
            "";


        if (phoneInput && lastOrderPhone) {

            phoneInput.value =
                lastOrderPhone;

        }


        if (
            phoneInput
            &&
            lastOrderPhone
            &&
            newOrderCode
        ) {

            // Mã đơn chỉ dùng để tự mở đúng đơn vừa đặt một lần.
            localStorage.removeItem(
                "orderCode"
            );


            searchOrder(
                newOrderCode
            );

        }

    }
);


window.searchOrder =
    searchOrder;


// =========================================================
// SEARCH
// =========================================================

async function searchOrder(
    focusOrderCode = ""
) {

    const input =
        document.getElementById(
            "phone"
        );


    const phone =
        input?.value.trim()
        ||
        "";


    if (!phone) {

        alert(
            "Vui lòng nhập số điện thoại."
        );


        input?.focus();


        return;

    }


    currentPhone =
        phone;


    try {

        const response =
            await fetch(
                `/api/orders/${encodeURIComponent(phone)}`,
                {
                    cache:
                        "no-store"
                }
            );


        const data =
            await safeJson(
                response
            );


        if (
            !response.ok
            ||
            !Array.isArray(
                data
            )
        ) {

            throw new Error(
                data?.message
                ||
                "Không thể tra cứu đơn hàng."
            );

        }


        const ordersToDisplay =
            focusOrderCode
                ? data.filter(
                    (order) =>
                        order.code ===
                        focusOrderCode
                )
                : data;


        if (
            ordersToDisplay.length ===
            0
        ) {

            stopTracking();

            destroyTrackingMaps();

            showNotFound();


            return;

        }


        currentOrders =
            ordersToDisplay;


        renderOrders(
            ordersToDisplay
        );


        if (
            ordersToDisplay.some(
                (order) =>
                    order.status ===
                    "Đang giao"
            )
        ) {

            startTracking();

        }
        else {

            stopTracking();

        }

    }
    catch (error) {

        console.error(
            "Order search error:",
            error
        );


        alert(
            error.message
            ||
            "Không thể kết nối máy chủ."
        );

    }

}


function showNotFound() {

    const box =
        document.getElementById(
            "order-result"
        );


    if (!box) {
        return;
    }


    box.innerHTML =
        `
        <div class="tracking-empty">

            <div class="tracking-empty-icon">
                📦
            </div>

            <h3>
                Không tìm thấy đơn hàng
            </h3>

            <p>
                Kiểm tra lại số điện thoại đã dùng khi đặt hàng.
            </p>

        </div>
        `;

}


// =========================================================
// RENDER
// =========================================================

function renderOrders(
    orders
) {

    stopTrackingAnimations();

    destroyTrackingMaps();


    const box =
        document.getElementById(
            "order-result"
        );


    if (!box) {
        return;
    }


    box.innerHTML =
        orders
            .map(
                renderOrderCard
            )
            .join(
                ""
            );


    orders
        .filter(
            (order) =>
                order.status ===
                "Đang giao"
        )
        .forEach(
            (order) => {

                window.setTimeout(
                    () => {

                        initTrackingMap(
                            order
                        );

                    },
                    80
                );

            }
        );

}


function renderOrderCard(
    order
) {

    const status =
        String(
            order.status
            ||
            ""
        );


    const step =
        getStatusStep(
            status
        );


    const code =
        escapeHTML(
            order.code
            ||
            ""
        );


    const driverName =
        escapeHTML(
            order.driverName
            ||
            "Đang cập nhật"
        );


    const total =
        formatMoney(
            order.total
            ||
            0
        );


    const hasDestination =
        Number.isFinite(
            Number(
                order.latitude
            )
        )
        &&
        Number.isFinite(
            Number(
                order.longitude
            )
        );


    const mapSection =
        status ===
        "Đang giao"

            ? `
            <section
                class="customer-live-map-panel"
                data-order-code="${code}"
                data-destination-lat="${numberOrBlank(order.latitude)}"
                data-destination-lng="${numberOrBlank(order.longitude)}"
            >

                <div class="tracking-map-heading">

                    <div>

                        <span class="tracking-map-eyebrow">
                            THEO DÕI TRỰC TIẾP
                        </span>

                        <h3>
                            🛵 Shipper đang trên đường
                        </h3>

                        <p class="tracking-map-message">
                            Đang lấy vị trí shipper...
                        </p>

                    </div>


                    <span class="tracking-live-badge">
                        Đang kết nối
                    </span>

                </div>


                <div class="tracking-map-metrics">

                    <div>

                        <span>
                            Shipper
                        </span>

                        <strong class="tracking-driver-name">
                            ${driverName}
                        </strong>

                    </div>


                    <div>

                        <span>
                            Khoảng cách
                        </span>

                        <strong class="tracking-distance">
                            -- km
                        </strong>

                    </div>


                    <div>

                        <span>
                            ETA
                        </span>

                        <strong class="tracking-eta">
                            -- phút
                        </strong>

                    </div>


                    <div>

                        <span>
                            GPS cập nhật
                        </span>

                        <strong class="tracking-gps-time">
                            --
                        </strong>

                    </div>

                </div>


                ${
                    hasDestination

                        ? `
                        <div class="customer-live-map">
                        </div>
                        `

                        : `
                        <div class="tracking-map-unavailable">
                            Đơn hàng chưa có tọa độ giao hàng.
                        </div>
                        `
                }

            </section>
            `

            : "";


    return `
        <article class="order-card live-order-card">

            <div class="order-heading">

                <div>

                    <p class="order-label">
                        MÃ ĐƠN HÀNG
                    </p>

                    <h2>
                        #${code}
                    </h2>

                    <small class="tracking-created-time">
                        ${escapeHTML(order.createdAt || "")}
                    </small>

                </div>


                <span
                    class="status-badge ${statusClass(status)}"
                >
                    ${escapeHTML(status)}
                </span>

            </div>


            <div class="customer-status-tracker">

                ${createStatusStep(
                    1,
                    step,
                    "✓",
                    "Đã tiếp nhận"
                )}

                ${createStatusConnector(
                    1,
                    step
                )}

                ${createStatusStep(
                    2,
                    step,
                    "🍜",
                    "Đang chuẩn bị"
                )}

                ${createStatusConnector(
                    2,
                    step
                )}

                ${createStatusStep(
                    3,
                    step,
                    "🛵",
                    "Đang giao"
                )}

                ${createStatusConnector(
                    3,
                    step
                )}

                ${createStatusStep(
                    4,
                    step,
                    "✓",
                    "Hoàn thành"
                )}

            </div>


            <div class="tracking-order-info">

                <div>

                    <span>
                        Khách hàng
                    </span>

                    <strong>
                        ${escapeHTML(order.name || "Chưa cập nhật")}
                    </strong>

                </div>


                <div>

                    <span>
                        Địa chỉ giao hàng
                    </span>

                    <strong>
                        ${escapeHTML(order.address || "Chưa cập nhật")}
                    </strong>

                </div>


                <div>

                    <span>
                        Tổng thanh toán
                    </span>

                    <strong class="tracking-total">
                        ${total}
                    </strong>

                </div>

            </div>


            ${mapSection}

        </article>
    `;

}


// =========================================================
// STATUS
// =========================================================

function createStatusStep(
    index,
    current,
    icon,
    label
) {

    const completed =
        current >=
        index;


    const active =
        current ===
        index;


    return `
        <div
            class="
                customer-status-step
                ${completed ? "completed" : ""}
                ${active ? "active" : ""}
            "
        >

            <div class="customer-status-icon">
                ${icon}
            </div>

            <strong>
                ${label}
            </strong>

        </div>
    `;

}


function createStatusConnector(
    index,
    current
) {

    return `
        <div
            class="
                customer-status-line
                ${current > index ? "completed" : ""}
            "
        >
        </div>
    `;

}


function getStatusStep(
    status
) {

    switch (
        status
    ) {

        case "Đã tiếp nhận":

            return 1;


        case "Đã giao shipper":

        case "Đang chuẩn bị":

            return 2;


        case "Đang giao":

            return 3;


        case "Hoàn thành":

            return 4;


        case "Không giao được":

        case "Đã hủy":

            return 3;


        default:

            return 1;

    }

}


function statusClass(
    status
) {

    switch (
        status
    ) {

        case "Đã tiếp nhận":

            return "received";


        case "Đã giao shipper":

            return "assigned";


        case "Đang chuẩn bị":

            return "preparing";


        case "Đang giao":

            return "delivering";


        case "Hoàn thành":

            return "completed";


        case "Không giao được":

            return "failed";


        case "Đã hủy":

            return "cancelled";


        default:

            return "neutral";

    }

}


// =========================================================
// MAP INIT
// =========================================================

function initTrackingMap(
    order
) {

    if (
        typeof L ===
        "undefined"
    ) {

        return;

    }


    const panel = [
        ...document.querySelectorAll(
            ".customer-live-map-panel"
        )
    ]
        .find(
            (element) => {

                return (
                    element.dataset.orderCode
                    ===
                    String(
                        order.code
                    )
                );

            }
        );


    if (!panel) {
        return;
    }


    const mapElement =
        panel.querySelector(
            ".customer-live-map"
        );


    if (
        !mapElement ||
        mapElement.dataset.mapReady ===
        "1"
    ) {

        return;

    }


    const destinationLat =
        Number(
            panel.dataset.destinationLat
        );


    const destinationLng =
        Number(
            panel.dataset.destinationLng
        );


    if (
        !Number.isFinite(
            destinationLat
        )
        ||
        !Number.isFinite(
            destinationLng
        )
    ) {

        return;

    }


    const map =
        L.map(
            mapElement,
            {
                zoomControl:
                    true
            }
        ).setView(
            [
                destinationLat,
                destinationLng
            ],
            15
        );


    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {

            maxZoom:
                19,

            attribution:
                "&copy; OpenStreetMap"

        }
    ).addTo(
        map
    );


    const customerIcon =
        L.divIcon({

            className:
                "tracking-customer-marker-wrap",

            html:
                '<div class="tracking-customer-marker">📍</div>',

            iconSize:
                [44, 50],

            iconAnchor:
                [22, 46]

        });


    L.marker(
        [
            destinationLat,
            destinationLng
        ],
        {
            icon:
                customerIcon
        }
    )
        .addTo(
            map
        )
        .bindPopup(
            "<strong>Địa chỉ nhận hàng</strong>"
        );


    const state = {

        orderCode:
            String(
                order.code
            ),

        panel,

        mapElement,

        map,

        destination: {
            lat:
                destinationLat,
            lng:
                destinationLng
        },

        driverMarker:
            null,

        routeLayer:
            null,

        routePoints:
            [],

        lastDriverPosition:
            null,

        lastRoutePosition:
            null,

        lastRouteAt:
            0,

        routeLoading:
            false,

        animationFrame:
            null,

        hasFittedBounds:
            false

    };


    trackingMaps.set(
        state.orderCode,
        state
    );


    mapElement.dataset.mapReady =
        "1";


    window.setTimeout(
        () => {

            map.invalidateSize();

        },
        120
    );


    pollTrackingForOrder(
        state.orderCode,
        true
    );

}


function createCustomerDriverIcon(
    bearing = 0
) {

    return L.divIcon({

        className:
            "tracking-driver-marker-wrap",

        html:
            `
            <div class="tracking-driver-marker">

                <div
                    class="tracking-bike-body"
                    style="transform: rotate(${bearing}deg)"
                >
                    🛵
                </div>

            </div>
            `,

        iconSize:
            [56, 56],

        iconAnchor:
            [28, 28]

    });

}


// =========================================================
// TRACKING REQUEST
// =========================================================

async function pollTrackingForOrder(
    orderCode,
    forceRoute = false
) {

    if (
        !currentPhone ||
        !orderCode
    ) {

        return;

    }


    const state =
        trackingMaps.get(
            String(
                orderCode
            )
        );


    if (!state) {
        return;
    }


    try {

        const response =
            await fetch(
                `/api/orders/${encodeURIComponent(orderCode)}/tracking?phone=${encodeURIComponent(currentPhone)}`,
                {
                    cache:
                        "no-store"
                }
            );


        const data =
            await safeJson(
                response
            );


        if (
            !response.ok ||
            !data.success
        ) {

            throw new Error(
                data.message
                ||
                "Không lấy được vị trí shipper."
            );

        }


        updateTrackingPanel(
            state,
            data,
            forceRoute
        );

    }
    catch (error) {

        console.error(
            "Tracking error:",
            error
        );


        setTrackingConnectionState(
            state,
            error.message
            ||
            "Mất kết nối GPS",
            false
        );

    }

}


// =========================================================
// UPDATE MAP
// =========================================================

function updateTrackingPanel(
    state,
    data,
    forceRoute = false
) {

    const driver =
        data.driver;


    if (!driver) {

        setTrackingConnectionState(
            state,
            data.message
            ||
            "Shipper chưa gửi GPS",
            false
        );


        return;

    }


    const lat =
        Number(
            driver.latitude
        );


    const lng =
        Number(
            driver.longitude
        );


    if (
        !Number.isFinite(
            lat
        )
        ||
        !Number.isFinite(
            lng
        )
    ) {

        setTrackingConnectionState(
            state,
            "GPS shipper không hợp lệ",
            false
        );


        return;

    }


    const current = {
        lat,
        lng
    };


    const snapped =
        state.routePoints.length

            ? snapPositionToRoute(
                state.routePoints,
                current
            )

            : current;


    const bearing =
        state.lastDriverPosition

            ? calculateBearing(
                state.lastDriverPosition.lat,
                state.lastDriverPosition.lng,
                snapped.lat,
                snapped.lng
            )

            : 0;


    if (
        !state.driverMarker
    ) {

        state.driverMarker =
            L.marker(
                [
                    snapped.lat,
                    snapped.lng
                ],
                {

                    icon:
                        createCustomerDriverIcon(
                            bearing
                        ),

                    zIndexOffset:
                        1000

                }
            )
                .addTo(
                    state.map
                )
                .bindPopup(
                    `<strong>${escapeHTML(driver.name || "Shipper")}</strong><br>Đang giao đơn #${escapeHTML(state.orderCode)}`
                );

    }
    else {

        animateCustomerDriverMarker(
            state,
            snapped,
            bearing
        );

    }


    state.lastDriverPosition = {
        lat:
            snapped.lat,
        lng:
            snapped.lng
    };


    const name =
        state.panel.querySelector(
            ".tracking-driver-name"
        );


    const gpsTime =
        state.panel.querySelector(
            ".tracking-gps-time"
        );


    if (name) {

        name.textContent =
            driver.name
            ||
            "Shipper";

    }


    if (gpsTime) {

        gpsTime.textContent =
            driver.updatedAt
            ||
            "Vừa cập nhật";

    }


    const isFresh =
        Boolean(
            driver.isFresh
        );


    setTrackingConnectionState(
        state,
        isFresh

            ? "Shipper đang di chuyển tới bạn"

            : "GPS shipper đang cập nhật chậm",
        isFresh
    );


    if (
        !state.hasFittedBounds
    ) {

        state.map.fitBounds(
            L.latLngBounds([
                [
                    snapped.lat,
                    snapped.lng
                ],
                [
                    state.destination.lat,
                    state.destination.lng
                ]
            ]),
            {

                padding:
                    [45, 45],

                maxZoom:
                    16

            }
        );


        state.hasFittedBounds =
            true;

    }


    refreshCustomerRoute(
        state,
        current,
        forceRoute
    );

}


function setTrackingConnectionState(
    state,
    message,
    isLive
) {

    const messageElement =
        state.panel.querySelector(
            ".tracking-map-message"
        );


    const badge =
        state.panel.querySelector(
            ".tracking-live-badge"
        );


    if (messageElement) {

        messageElement.textContent =
            message;

    }


    if (badge) {

        badge.textContent =
            isLive

                ? "● Trực tiếp"

                : "GPS chậm";


        badge.classList.toggle(
            "is-live",
            isLive
        );


        badge.classList.toggle(
            "is-stale",
            !isLive
        );

    }

}


// =========================================================
// MARKER ANIMATION
// =========================================================

function animateCustomerDriverMarker(
    state,
    targetPosition,
    bearing
) {

    if (
        !state.driverMarker
    ) {

        return;

    }


    if (
        state.animationFrame
    ) {

        cancelAnimationFrame(
            state.animationFrame
        );

    }


    const current =
        state.driverMarker.getLatLng();


    const start = {
        lat:
            current.lat,
        lng:
            current.lng
    };


    const duration =
        2300;


    const startedAt =
        performance.now();


    function frame(
        now
    ) {

        const progress =
            Math.min(
                (
                    now -
                    startedAt
                )
                /
                duration,
                1
            );


        const eased =
            1
            -
            Math.pow(
                1 -
                progress,
                3
            );


        const lat =
            start.lat
            +
            (
                targetPosition.lat
                -
                start.lat
            )
            *
            eased;


        const lng =
            start.lng
            +
            (
                targetPosition.lng
                -
                start.lng
            )
            *
            eased;


        state.driverMarker.setLatLng([
            lat,
            lng
        ]);


        const bike =
            state.driverMarker
                .getElement()
                ?.querySelector(
                    ".tracking-bike-body"
                );


        if (bike) {

            bike.style.transform =
                `rotate(${bearing}deg)`;

        }


        if (
            progress < 1
        ) {

            state.animationFrame =
                requestAnimationFrame(
                    frame
                );

        }
        else {

            state.animationFrame =
                null;

        }

    }


    state.animationFrame =
        requestAnimationFrame(
            frame
        );

}


// =========================================================
// ROUTING
// =========================================================

async function refreshCustomerRoute(
    state,
    position,
    force = false
) {

    if (
        state.routeLoading
    ) {

        return;

    }


    const now =
        Date.now();


    const moved =
        state.lastRoutePosition

            ? distanceBetweenMeters(
                state.lastRoutePosition.lat,
                state.lastRoutePosition.lng,
                position.lat,
                position.lng
            )

            : Number.POSITIVE_INFINITY;


    if (
        !force &&
        moved < 25 &&
        now -
        state.lastRouteAt
        <
        15000
    ) {

        return;

    }


    state.routeLoading =
        true;


    try {

        const url =
            "https://router.project-osrm.org/route/v1/driving/"
            +
            `${encodeURIComponent(position.lng)},${encodeURIComponent(position.lat)};`
            +
            `${encodeURIComponent(state.destination.lng)},${encodeURIComponent(state.destination.lat)}`
            +
            "?overview=full&geometries=geojson&steps=false";


        const response =
            await fetch(
                url
            );


        if (
            !response.ok
        ) {

            throw new Error(
                "Routing service unavailable"
            );

        }


        const data =
            await response.json();


        const route =
            data.routes?.[0];


        if (!route) {

            throw new Error(
                "Không có tuyến đường."
            );

        }


        const points =
            route.geometry.coordinates.map(
                (
                    [
                        lng,
                        lat
                    ]
                ) => {

                    return [
                        lat,
                        lng
                    ];

                }
            );


        state.routePoints =
            points;


        if (
            state.routeLayer
        ) {

            state.routeLayer.setLatLngs(
                points
            );

        }
        else {

            state.routeLayer =
                L.polyline(
                    points,
                    {

                        color:
                            "#7a0c1e",

                        weight:
                            5,

                        opacity:
                            0.86

                    }
                ).addTo(
                    state.map
                );

        }


        updateCustomerRouteMetrics(
            state,
            route.distance,
            route.duration
        );


        state.lastRoutePosition = {
            lat:
                position.lat,
            lng:
                position.lng
        };


        state.lastRouteAt =
            now;

    }
    catch (error) {

        console.warn(
            "OSRM route error:",
            error
        );


        const distance =
            distanceBetweenMeters(
                position.lat,
                position.lng,
                state.destination.lat,
                state.destination.lng
            );


        const fallback = [
            [
                position.lat,
                position.lng
            ],
            [
                state.destination.lat,
                state.destination.lng
            ]
        ];


        state.routePoints =
            fallback;


        if (
            state.routeLayer
        ) {

            state.routeLayer.setLatLngs(
                fallback
            );

        }
        else {

            state.routeLayer =
                L.polyline(
                    fallback,
                    {

                        color:
                            "#7a0c1e",

                        weight:
                            4,

                        opacity:
                            0.55,

                        dashArray:
                            "8 10"

                    }
                ).addTo(
                    state.map
                );

        }


        updateCustomerRouteMetrics(
            state,
            distance,
            null
        );

    }
    finally {

        state.routeLoading =
            false;

    }

}


function updateCustomerRouteMetrics(
    state,
    distanceMeters,
    durationSeconds
) {

    const distance =
        state.panel.querySelector(
            ".tracking-distance"
        );


    const eta =
        state.panel.querySelector(
            ".tracking-eta"
        );


    if (distance) {

        distance.textContent =
            formatDistance(
                distanceMeters
            );

    }


    if (eta) {

        eta.textContent =
            Number.isFinite(
                Number(
                    durationSeconds
                )
            )

                ? formatDuration(
                    durationSeconds
                )

                : "Đang tính";

    }

}


// =========================================================
// POLLING
// =========================================================

function startTracking() {

    stopTracking();


    trackingMaps.forEach(
        (state) => {

            pollTrackingForOrder(
                state.orderCode,
                true
            );

        }
    );


    trackingTimer =
        window.setInterval(
            () => {

                trackingMaps.forEach(
                    (state) => {

                        pollTrackingForOrder(
                            state.orderCode,
                            false
                        );

                    }
                );

            },
            3000
        );

}


function stopTracking() {

    if (
        trackingTimer
    ) {

        clearInterval(
            trackingTimer
        );


        trackingTimer =
            null;

    }

}


function stopTrackingAnimations() {

    trackingMaps.forEach(
        (state) => {

            if (
                state.animationFrame
            ) {

                cancelAnimationFrame(
                    state.animationFrame
                );

            }

        }
    );

}


function destroyTrackingMaps() {

    stopTrackingAnimations();


    trackingMaps.forEach(
        (state) => {

            try {

                state.map.remove();

            }
            catch (error) {

                console.debug(
                    error
                );

            }

        }
    );


    trackingMaps.clear();

}


// =========================================================
// HELPERS
// =========================================================

function numberOrBlank(
    value
) {

    const number =
        Number(
            value
        );


    return Number.isFinite(
        number
    )

        ? String(
            number
        )

        : "";

}


function formatMoney(
    value
) {

    const number =
        Number(
            value
        )
        ||
        0;


    return `${
        number.toLocaleString(
            "vi-VN",
            {
                maximumFractionDigits:
                    0
            }
        )
    } ₫`;

}


function formatDistance(
    distanceMeters
) {

    const meters =
        Number(
            distanceMeters
        );


    if (
        !Number.isFinite(
            meters
        )
    ) {

        return "-- km";

    }


    if (
        meters < 1000
    ) {

        return `${Math.max(Math.round(meters), 0)} m`;

    }


    return `${
        (
            meters / 1000
        ).toLocaleString(
            "vi-VN",
            {
                minimumFractionDigits:
                    1,

                maximumFractionDigits:
                    1
            }
        )
    } km`;

}


function formatDuration(
    durationSeconds
) {

    const seconds =
        Number(
            durationSeconds
        );


    if (
        !Number.isFinite(
            seconds
        )
    ) {

        return "-- phút";

    }


    const minutes =
        Math.max(
            Math.ceil(
                seconds / 60
            ),
            1
        );


    if (
        minutes < 60
    ) {

        return `${minutes} phút`;

    }


    const hours =
        Math.floor(
            minutes / 60
        );


    const remaining =
        minutes %
        60;


    return remaining

        ? `${hours} giờ ${remaining} phút`

        : `${hours} giờ`;

}


function distanceBetweenMeters(
    lat1,
    lng1,
    lat2,
    lng2
) {

    const earthRadius =
        6371000;


    const toRadians =
        Math.PI
        /
        180;


    const dLat =
        (
            lat2 -
            lat1
        )
        *
        toRadians;


    const dLng =
        (
            lng2 -
            lng1
        )
        *
        toRadians;


    const a =
        Math.sin(
            dLat / 2
        ) ** 2
        +
        Math.cos(
            lat1
            *
            toRadians
        )
        *
        Math.cos(
            lat2
            *
            toRadians
        )
        *
        Math.sin(
            dLng / 2
        ) ** 2;


    return earthRadius
        *
        2
        *
        Math.atan2(
            Math.sqrt(
                a
            ),
            Math.sqrt(
                1 - a
            )
        );

}


function calculateBearing(
    lat1,
    lng1,
    lat2,
    lng2
) {

    const toRadians =
        Math.PI
        /
        180;


    const toDegrees =
        180
        /
        Math.PI;


    const phi1 =
        lat1
        *
        toRadians;


    const phi2 =
        lat2
        *
        toRadians;


    const deltaLambda =
        (
            lng2 -
            lng1
        )
        *
        toRadians;


    const y =
        Math.sin(
            deltaLambda
        )
        *
        Math.cos(
            phi2
        );


    const x =
        Math.cos(
            phi1
        )
        *
        Math.sin(
            phi2
        )
        -
        Math.sin(
            phi1
        )
        *
        Math.cos(
            phi2
        )
        *
        Math.cos(
            deltaLambda
        );


    return (
        Math.atan2(
            y,
            x
        )
        *
        toDegrees
        +
        360
    )
    %
    360;

}


function snapPositionToRoute(
    points,
    position
) {

    if (
        !Array.isArray(
            points
        )
        ||
        points.length ===
        0
    ) {

        return position;

    }


    let bestPoint =
        null;


    let bestDistance =
        Number.POSITIVE_INFINITY;


    for (
        const point
        of points
    ) {

        const distance =
            distanceBetweenMeters(
                position.lat,
                position.lng,
                point[0],
                point[1]
            );


        if (
            distance <
            bestDistance
        ) {

            bestDistance =
                distance;


            bestPoint =
                point;

        }

    }


    if (
        !bestPoint ||
        bestDistance > 80
    ) {

        return position;

    }


    return {
        lat:
            bestPoint[0],
        lng:
            bestPoint[1]
    };

}


function escapeHTML(
    value
) {

    const div =
        document.createElement(
            "div"
        );


    div.textContent =
        String(
            value
            ??
            ""
        );


    return div.innerHTML;

}


async function safeJson(
    response
) {

    try {

        return await response.json();

    }
    catch (error) {

        console.error(
            "Invalid JSON:",
            error
        );


        return {

            success:
                false,

            message:
                "Server trả về dữ liệu không hợp lệ."

        };

    }

}


window.addEventListener(
    "beforeunload",
    () => {

        stopTracking();

        destroyTrackingMaps();

    }
);
