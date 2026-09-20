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

        const phone =
            document.getElementById("phone")
            .value
            .trim();


        if (!phone) {

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


            const orders =
                await response.json();



            if (
                !orders ||
                orders.length === 0
            ) {

                showNotFound();

                stopTracking();

                return;

            }



            renderOrders(
                orders
            );



            const shipping =
                orders.some(order =>
                    order.status === "Đang giao"
                );



            if (shipping) {

                startTracking();

            }
            else {

                stopTracking();

            }



        }
        catch(error) {


            console.error(
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

                    <div>

                        <p>
                            Tiền món:
                            ${formatMoney(order.foodMoney)}
                        </p>


                        <p>
                            Phí giao hàng:
                            ${formatMoney(order.shippingFee)}
                        </p>

                    </div>


                    <strong>
                        ${formatMoney(order.total)}
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


    const mapId =
        "driver-map-" + order.code;


    const mapElement =
        document.getElementById(mapId);



    if (!mapElement) {

        console.log(
            "Không tìm thấy map:",
            mapId
        );

        return;

    }



    // Xóa map cũ nếu có

    if (driverMap) {

        driverMap.remove();

        driverMap = null;

        driverMarker = null;

    }



    const SHOP_LAT = 21.0338;
    const SHOP_LNG = 105.8019;



    const latitude =
        Number(order.latitude)
        || SHOP_LAT;


    const longitude =
        Number(order.longitude)
        || SHOP_LNG;



    // Tạo map

    driverMap =
        L.map(
            mapElement
        ).setView(
            [
                latitude,
                longitude
            ],
            16
        );



    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {

            maxZoom:19,

            attribution:
            "&copy; OpenStreetMap"

        }

    ).addTo(
        driverMap
    );




    const driverIcon =
        L.divIcon({

            className:
            "custom-driver-icon",

            html:
            `
            <div class="driver-marker">
                🛵
            </div>
            `,


            iconSize:
            [
                58,
                70
            ],

            iconAnchor:
            [
                29,
                60
            ]

        });



    driverMarker =
        L.marker(
            [
                latitude,
                longitude
            ],
            {
                icon:
                driverIcon
            }
        )
        .addTo(
            driverMap
        );



    driverMarker.bindPopup(

        `
        <div class="driver-popup">

            <div class="driver-popup-name">

                🛵
                ${order.driverName || "Shipper"}

            </div>


            <div class="driver-popup-status">

                ● Đang giao hàng

            </div>

        </div>
        `

    );


    driverMarker.openPopup();



    // Fix lỗi map trắng khi render động

    setTimeout(()=>{

        driverMap.invalidateSize();

    },500);



}


    // =========================================================
    // LẤY VỊ TRÍ SHIPPER
    // =========================================================

async function updateDriverLocation(){


    if(
        !currentPhone ||
        !driverMap ||
        !driverMarker
    ){

        return;

    }



    try{


        const response =
            await fetch(
                "/api/orders/"
                +
                encodeURIComponent(
                    currentPhone
                )
            );



        const orders =
            await response.json();



        if(!Array.isArray(orders)){

            return;

        }



        const order =
            orders.find(
                x =>
                x.status === "Đang giao"
            );



        if(!order){

            return;

        }



        const lat =
            Number(order.latitude);



        const lng =
            Number(order.longitude);



        if(
            !lat ||
            !lng
        ){

            return;

        }



        const position =
        [
            lat,
            lng
        ];



        driverMarker.setLatLng(
            position
        );


        driverMap.panTo(
            position
        );



    }

    catch(error){

        console.error(
            "GPS lỗi:",
            error
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

    function renderOrders(orders) {


        const box =
            document.getElementById(
                "order-result"
            );


        box.innerHTML = "";


        orders.forEach(order => {


            box.innerHTML += `

            <div class="order-history">


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



                <div class="info-row">

                    <span>
                        Ngày đặt
                    </span>


                    <strong>
                        ${order.createdAt}
                    </strong>

                </div>



                <div class="info-row">

                    <span>
                        Khách hàng
                    </span>


                    <strong>
                        ${escapeHTML(order.name)}
                    </strong>

                </div>



                <div class="info-row">

                    <span>
                        Địa chỉ
                    </span>


                    <strong>
                        ${escapeHTML(order.address)}
                    </strong>

                </div>



                <div class="info-row">

                    <span>
                        Trạng thái
                    </span>


                    <strong class="status-text">

                        ${order.status}

                    </strong>

                </div>



                <div class="order-total">


                    <p>
                        Tiền món:
                        ${formatMoney(order.foodTotal)}
                    </p>


                    <p>
                        Phí giao hàng:
                        ${formatMoney(order.shippingFee)}
                    </p>


                    <strong>
                        ${formatMoney(order.total)}
                    </strong>


                </div>


                ${
                    order.status === "Đang giao"

                    ?

                    `

                    <div class="driver">

                        <h3>
                            🛵 Tài xế đang giao hàng
                        </h3>


                        <p>
                            ${
                                order.driverName ||
                                "Đang tìm tài xế"
                            }
                        </p>


                    </div>


                    <div class="map-section">

                        <h3>
                            📍 Vị trí tài xế
                        </h3>


                        <div
                            id="driver-map-${order.code}"
                            class="driver-map"
                        ></div>

                    </div>

                    `

                    :

                    ""

                }


            </div>


            `;



            // tạo map cho đơn đang giao

            if(order.status === "Đang giao"){

                setTimeout(()=>{

                    initDriverMap(order);

                },200);

            }


        });


    }