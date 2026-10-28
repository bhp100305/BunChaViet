// =========================================================
// BUN CHA VIET - CHECKOUT
// Cart + map + shipping + payment + order payload
// Email OTP itself is handled by /static/js/email-otp.js
// =========================================================

let cart = JSON.parse(localStorage.getItem("cart") || "[]");
let shippingFee = 0;
let marker = null;
let typingTimer = null;
let orderSubmitting = false;
let createdPaymentOrder = null;
let map = null;

const SHOP_LAT = 21.0338;
const SHOP_LNG = 105.8019;

const $ = (id) => document.getElementById(id);

const checkoutItems = $("checkout-items");
const foodTotalElement = $("food-total");
const checkoutTotalElement = $("checkout-total");
const distanceElement = $("distance");
const shippingFeeElement = $("shipping-fee");

const fullnameInput = $("fullname");
const phoneInput = $("phone");
const emailInput = $("email");
const addressInput = $("address");
const latitudeInput = $("latitude");
const longitudeInput = $("longitude");
const noteInput = $("note");

const suggestionBox = $("suggestions");

const orderButton = $("order-btn");
const currentLocationButton = $("current-location");
const searchLocationButton = $("search-location");

const paymentModal = $("bank-transfer-modal");
const closePaymentModalButton = $("close-payment-modal");
const confirmTransferButton = $("confirm-transfer-btn");
const payLaterButton = $("pay-later-btn");

const paymentOrderCode = $("payment-order-code");
const paymentAmount = $("payment-amount");
const paymentContent = $("payment-content");


// =========================================================
// MONEY
// =========================================================

function formatMoney(value) {

    return `${(
        Number(value)
        ||
        0
    ).toLocaleString("vi-VN")} ₫`;

}


// =========================================================
// ESCAPE HTML
// =========================================================

function escapeHTML(value) {

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


// =========================================================
// READ JSON SAFELY
// =========================================================

async function readJsonResponse(response) {

    try {

        return await response.json();

    }
    catch (error) {

        console.error(
            "Server trả về dữ liệu không phải JSON:",
            error
        );

        return {

            success:
                false,

            message:
                "Máy chủ trả về dữ liệu không hợp lệ."

        };

    }

}


// =========================================================
// FOOD TOTAL
// =========================================================

function getFoodTotal() {

    return cart.reduce(
        (
            sum,
            item
        ) => {

            const price =
                Number(
                    item.price
                )
                ||
                0;

            const quantity =
                Number(
                    item.quantity
                )
                ||
                0;

            return (
                sum
                +
                price
                *
                quantity
            );

        },
        0
    );

}


// =========================================================
// PAYMENT METHOD
// =========================================================

function getSelectedPaymentMethod() {

    return (
        document.querySelector(
            'input[name="payment-method"]:checked'
        )?.value
        ||
        "CASH"
    );

}


// =========================================================
// BUTTON LOADING
// =========================================================

function setButtonLoading(
    button,
    loading,
    loadingText,
    originalText
) {

    if (
        !button
    ) {

        return;

    }

    button.disabled =
        loading;

    button.textContent =
        loading
            ?
            loadingText
            :
            originalText;

}


// =========================================================
// RENDER CHECKOUT CART
// =========================================================

function renderCheckout() {

    if (
        !checkoutItems
        ||
        !foodTotalElement
        ||
        !checkoutTotalElement
    ) {

        return;

    }

    const foodTotal =
        getFoodTotal();

    checkoutItems.innerHTML =
        "";

    // =====================================================
    // EMPTY CART
    // =====================================================

    if (
        cart.length ===
        0
    ) {

        checkoutItems.innerHTML =
            `
            <div class="checkout-empty">

                <div class="checkout-empty-icon">
                    🛒
                </div>

                <strong>
                    Giỏ hàng đang trống
                </strong>

                <p>
                    Quay lại thực đơn để chọn món trước khi đặt hàng.
                </p>

            </div>
            `;

        foodTotalElement.textContent =
            formatMoney(
                0
            );

        checkoutTotalElement.textContent =
            formatMoney(
                shippingFee
            );

        if (
            orderButton
        ) {

            orderButton.disabled =
                true;

        }

        return;

    }

    // =====================================================
    // CART ITEMS
    // =====================================================

    cart.forEach(
        (
            item
        ) => {

            const price =
                Number(
                    item.price
                )
                ||
                0;

            const quantity =
                Number(
                    item.quantity
                )
                ||
                0;

            const money =
                price
                *
                quantity;

            const row =
                document.createElement(
                    "div"
                );

            row.className =
                "checkout-item";

            const safeImage =
                encodeURIComponent(
                    String(
                        item.image
                        ||
                        ""
                    )
                )
                .replace(
                    /%2F/gi,
                    "/"
                );

            row.innerHTML =
                `
                <img
                    src="/static/images/${safeImage}"
                    alt="${escapeHTML(item.name || "Món ăn")}"
                    onerror="this.style.visibility='hidden'"
                >

                <div class="checkout-item-info">

                    <b>
                        ${escapeHTML(item.name || "Món ăn")}
                    </b>

                    <p>
                        ${quantity}
                        x
                        ${formatMoney(price)}
                    </p>

                </div>

                <strong class="checkout-item-money">
                    ${formatMoney(money)}
                </strong>
                `;

            checkoutItems.appendChild(
                row
            );

        }
    );

    foodTotalElement.textContent =
        formatMoney(
            foodTotal
        );

    checkoutTotalElement.textContent =
        formatMoney(
            foodTotal
            +
            shippingFee
        );

    if (
        orderButton
        &&
        !orderSubmitting
    ) {

        orderButton.disabled =
            false;

    }

}


// =========================================================
// MAP INITIALIZE
// =========================================================

if (
    typeof L !==
    "undefined"
    &&
    $("map")
) {

    map =
        L.map(
            "map"
        )
        .setView(
            [
                21.0285,
                105.8542
            ],
            13
        );

    L.tileLayer(
        "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        {

            maxZoom:
                19,

            attribution:
                "&copy; OpenStreetMap"

        }
    )
    .addTo(
        map
    );

}


// =========================================================
// SET MARKER
// =========================================================

async function setMarker(
    lat,
    lng,
    shouldReverseGeocode = true
) {

    const latitude =
        Number(
            lat
        );

    const longitude =
        Number(
            lng
        );

    if (
        !Number.isFinite(
            latitude
        )
        ||
        !Number.isFinite(
            longitude
        )
    ) {

        alert(
            "Tọa độ giao hàng không hợp lệ."
        );

        return;

    }

    if (
        map
    ) {

        if (
            marker
        ) {

            map.removeLayer(
                marker
            );

        }

        marker =
            L.marker(
                [
                    latitude,
                    longitude
                ]
            )
            .addTo(
                map
            );

        map.setView(
            [
                latitude,
                longitude
            ],
            16
        );

    }

    if (
        latitudeInput
    ) {

        latitudeInput.value =
            String(
                latitude
            );

    }

    if (
        longitudeInput
    ) {

        longitudeInput.value =
            String(
                longitude
            );

    }

    calculateShipping(
        latitude,
        longitude
    );

    if (
        shouldReverseGeocode
    ) {

        await reverseGeocode(
            latitude,
            longitude
        );

    }

}


// =========================================================
// DISTANCE
// =========================================================

function calculateDistance(
    lat1,
    lon1,
    lat2,
    lon2
) {

    const R =
        6371;

    const toRad =
        Math.PI
        /
        180;

    const dLat =
        (
            lat2
            -
            lat1
        )
        *
        toRad;

    const dLon =
        (
            lon2
            -
            lon1
        )
        *
        toRad;

    const a =

        Math.sin(
            dLat
            /
            2
        ) ** 2

        +

        Math.cos(
            lat1
            *
            toRad
        )

        *

        Math.cos(
            lat2
            *
            toRad
        )

        *

        Math.sin(
            dLon
            /
            2
        ) ** 2;

    const c =
        2
        *
        Math.atan2(

            Math.sqrt(
                a
            ),

            Math.sqrt(
                1
                -
                a
            )

        );

    return (
        R
        *
        c
    );

}


// =========================================================
// SHIPPING FEE
// =========================================================

function calculateShippingFee(
    distance
) {

    if (
        distance <=
        2
    ) {

        return 10000;

    }

    if (
        distance <=
        5
    ) {

        return 15000;

    }

    if (
        distance <=
        10
    ) {

        return 25000;

    }

    return 50000;

}


// =========================================================
// CALCULATE SHIPPING
// =========================================================

function calculateShipping(
    lat,
    lng
) {

    const distance =
        calculateDistance(

            SHOP_LAT,

            SHOP_LNG,

            Number(
                lat
            ),

            Number(
                lng
            )

        );

    shippingFee =
        calculateShippingFee(
            distance
        );

    if (
        distanceElement
    ) {

        distanceElement.textContent =
            `${distance.toFixed(1)} km`;

    }

    if (
        shippingFeeElement
    ) {

        shippingFeeElement.textContent =
            formatMoney(
                shippingFee
            );

    }

    renderCheckout();

}


// =========================================================
// REVERSE GEOCODE
// =========================================================

async function reverseGeocode(
    lat,
    lng
) {

    try {

        const url =

            `https://nominatim.openstreetmap.org/reverse`

            +

            `?format=json&lat=${encodeURIComponent(lat)}`

            +

            `&lon=${encodeURIComponent(lng)}&accept-language=vi`;

        const response =
            await fetch(
                url
            );

        if (
            !response.ok
        ) {

            return;

        }

        const data =
            await response.json();

        if (
            data.display_name
            &&
            addressInput
        ) {

            addressInput.value =
                data.display_name;

        }

    }
    catch (
        error
    ) {

        console.warn(
            "Reverse geocode error:",
            error
        );

    }

}


// =========================================================
// SEARCH ADDRESS
// =========================================================

async function searchAddress(
    keyword
) {

    if (
        !suggestionBox
    ) {

        return;

    }

    try {

        const url =

            `https://nominatim.openstreetmap.org/search`

            +

            `?format=json&limit=5&countrycodes=vn&accept-language=vi`

            +

            `&q=${encodeURIComponent(keyword)}`;

        const response =
            await fetch(
                url
            );

        if (
            !response.ok
        ) {

            throw new Error(
                "Không thể tìm địa chỉ."
            );

        }

        const data =
            await response.json();

        suggestionBox.innerHTML =
            "";

        if (
            !Array.isArray(
                data
            )
            ||
            data.length ===
            0
        ) {

            suggestionBox.innerHTML =
                `
                <div class="suggestion-empty">
                    Không tìm thấy địa chỉ phù hợp.
                </div>
                `;

            return;

        }

        data.forEach(
            (
                place
            ) => {

                const item =
                    document.createElement(
                        "button"
                    );

                item.type =
                    "button";

                item.className =
                    "suggestion-item";

                item.textContent =
                    `📍 ${place.display_name}`;

                item.addEventListener(
                    "click",
                    async () => {

                        if (
                            addressInput
                        ) {

                            addressInput.value =
                                place.display_name;

                        }

                        suggestionBox.innerHTML =
                            "";

                        await setMarker(

                            place.lat,

                            place.lon,

                            false

                        );

                    }
                );

                suggestionBox.appendChild(
                    item
                );

            }
        );

    }
    catch (
        error
    ) {

        console.error(
            "Address search error:",
            error
        );

        suggestionBox.innerHTML =
            `
            <div class="suggestion-empty">
                Không thể tìm địa chỉ lúc này.
            </div>
            `;

    }

}


// =========================================================
// ADDRESS INPUT SEARCH
// =========================================================

addressInput?.addEventListener(
    "input",
    function () {

        clearTimeout(
            typingTimer
        );

        const keyword =
            this.value.trim();

        if (
            keyword.length
            <
            3
        ) {

            if (
                suggestionBox
            ) {

                suggestionBox.innerHTML =
                    "";

            }

            return;

        }

        typingTimer =
            window.setTimeout(
                () => {

                    searchAddress(
                        keyword
                    );

                },
                500
            );

    }
);


// =========================================================
// SEARCH BUTTON
// =========================================================

searchLocationButton?.addEventListener(
    "click",
    () => {

        const keyword =
            addressInput?.value.trim()
            ||
            "";

        if (
            keyword.length
            <
            3
        ) {

            alert(
                "Vui lòng nhập địa chỉ cần tìm."
            );

            addressInput?.focus();

            return;

        }

        searchAddress(
            keyword
        );

    }
);


// =========================================================
// CLOSE ADDRESS SUGGESTIONS
// =========================================================

document.addEventListener(
    "click",
    (
        event
    ) => {

        if (
            !suggestionBox
            ||
            !addressInput
        ) {

            return;

        }

        if (
            !suggestionBox.contains(
                event.target
            )
            &&
            event.target !==
            addressInput
            &&
            event.target !==
            searchLocationButton
        ) {

            suggestionBox.innerHTML =
                "";

        }

    }
);


// =========================================================
// MAP CLICK
// =========================================================

map?.on(
    "click",
    (
        event
    ) => {

        setMarker(

            event.latlng.lat,

            event.latlng.lng

        );

    }
);


// =========================================================
// CURRENT LOCATION
// =========================================================

currentLocationButton?.addEventListener(
    "click",
    () => {

        if (
            !navigator.geolocation
        ) {

            alert(
                "Thiết bị không hỗ trợ lấy vị trí."
            );

            return;

        }

        const oldText =
            currentLocationButton.textContent;

        currentLocationButton.disabled =
            true;

        currentLocationButton.textContent =
            "Đang lấy vị trí...";

        navigator.geolocation.getCurrentPosition(

            async (
                position
            ) => {

                try {

                    await setMarker(

                        position.coords.latitude,

                        position.coords.longitude

                    );

                }
                finally {

                    currentLocationButton.disabled =
                        false;

                    currentLocationButton.textContent =
                        oldText;

                }

            },


            (
                error
            ) => {

                console.warn(
                    "Location error:",
                    error
                );

                currentLocationButton.disabled =
                    false;

                currentLocationButton.textContent =
                    oldText;

                if (
                    error.code ===
                    error.PERMISSION_DENIED
                ) {

                    alert(
                        "Bạn chưa cho phép trình duyệt truy cập vị trí."
                    );

                }
                else {

                    alert(
                        "Không lấy được vị trí hiện tại."
                    );

                }

            },


            {

                enableHighAccuracy:
                    true,

                timeout:
                    12000,

                maximumAge:
                    5000

            }

        );

    }
);


// =========================================================
// PAYMENT METHOD UI
// =========================================================

function refreshPaymentSelection() {

    document
        .querySelectorAll(
            ".payment-option"
        )
        .forEach(
            (
                option
            ) => {

                const radio =
                    option.querySelector(
                        'input[name="payment-method"]'
                    );

                option.classList.toggle(

                    "selected",

                    Boolean(
                        radio?.checked
                    )

                );

            }
        );

}


document
    .querySelectorAll(
        'input[name="payment-method"]'
    )
    .forEach(
        (
            radio
        ) => {

            radio.addEventListener(

                "change",

                refreshPaymentSelection

            );

        }
    );


// =========================================================
// BUILD ORDER PAYLOAD
// =========================================================

function buildOrderPayload() {

    return {

        customerName:
            fullnameInput?.value.trim()
            ||
            "",


        phone:
            phoneInput?.value.trim()
            ||
            "",


        // QUAN TRỌNG:
        // email này được gửi cùng /api/orders
        // để backend email_otp.py kiểm tra
        email:
            emailInput?.value
                .trim()
                .toLowerCase()
            ||
            "",


        address:
            addressInput?.value.trim()
            ||
            "",


        latitude:
            latitudeInput?.value
            ||
            "",


        longitude:
            longitudeInput?.value
            ||
            "",


        note:
            noteInput?.value.trim()
            ||
            "",


        shippingFee:
            shippingFee,


        paymentMethod:
            getSelectedPaymentMethod(),


        products:
            cart

    };

}


// =========================================================
// VALIDATE ORDER
// =========================================================

function validateOrder(
    order
) {

    if (
        cart.length ===
        0
    ) {

        alert(
            "Giỏ hàng đang trống."
        );

        return false;

    }


    if (
        !order.customerName
    ) {

        alert(
            "Vui lòng nhập họ tên."
        );

        fullnameInput?.focus();

        return false;

    }


    if (
        !order.phone
    ) {

        alert(
            "Vui lòng nhập số điện thoại."
        );

        phoneInput?.focus();

        return false;

    }


    if (
        !order.email
        ||
        !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(
            order.email
        )
    ) {

        alert(
            "Vui lòng nhập email hợp lệ và xác thực OTP."
        );

        emailInput?.focus();

        return false;

    }


    const normalizedPhone =
        order.phone.replace(
            /\s+/g,
            ""
        );

    if (
        !/^\+?[0-9]{9,12}$/.test(
            normalizedPhone
        )
    ) {

        alert(
            "Số điện thoại không hợp lệ."
        );

        phoneInput?.focus();

        return false;

    }


    if (
        !order.address
        ||
        !order.latitude
        ||
        !order.longitude
    ) {

        alert(
            "Vui lòng chọn vị trí giao hàng trên bản đồ."
        );

        return false;

    }


    if (
        ![
            "CASH",
            "BANK_TRANSFER"
        ].includes(
            order.paymentMethod
        )
    ) {

        alert(
            "Vui lòng chọn phương thức thanh toán."
        );

        return false;

    }


    return true;

}


// =========================================================
// CREATE ORDER
// =========================================================

orderButton?.addEventListener(
    "click",
    async () => {

        if (
            orderSubmitting
        ) {

            return;

        }

        const order =
            buildOrderPayload();

        if (
            !validateOrder(
                order
            )
        ) {

            return;

        }

        const originalText =
            orderButton.textContent;

        const calculatedTotal =
            getFoodTotal()
            +
            shippingFee;

        orderSubmitting =
            true;

        setButtonLoading(

            orderButton,

            true,

            "ĐANG TẠO ĐƠN...",

            originalText

        );

        try {

            const response =
                await fetch(
                    "/api/orders",
                    {

                        method:
                            "POST",

                        credentials:
                            "same-origin",

                        headers: {

                            "Content-Type":
                                "application/json"

                        },

                        body:
                            JSON.stringify(
                                order
                            )

                    }
                );

            const data =
                await readJsonResponse(
                    response
                );

            if (
                !response.ok
                ||
                !data.success
            ) {

                throw new Error(

                    data.message

                    ||

                    "Đặt hàng thất bại."

                );

            }

            // =================================================
            // SAVE LAST ORDER
            // =================================================

            localStorage.setItem(

                "orderCode",

                data.orderCode
                ||
                ""

            );

            localStorage.setItem(

                "lastOrderPhone",

                order.phone

            );


            // =================================================
            // CLEAR CART
            // =================================================

            cart =
                [];

            localStorage.removeItem(
                "cart"
            );


            // =================================================
            // SAVE CREATED ORDER
            // =================================================

            createdPaymentOrder = {

                orderCode:
                    data.orderCode,


                phone:
                    order.phone,


                totalAmount:
                    Number(
                        data.totalAmount
                    )
                    ||
                    calculatedTotal,


                paymentMethod:
                    data.paymentMethod
                    ||
                    order.paymentMethod

            };


            // =================================================
            // BANK TRANSFER
            // =================================================

            if (
                createdPaymentOrder.paymentMethod
                ===
                "BANK_TRANSFER"
            ) {

                showBankTransferModal(
                    createdPaymentOrder
                );

                return;

            }


            // =================================================
            // CASH
            // =================================================

            alert(

                `Đặt hàng thành công. Mã đơn: ${data.orderCode}`

            );

            window.location.href =
                "/track-order";

        }
        catch (
            error
        ) {

            console.error(
                "Create order error:",
                error
            );

            alert(

                error.message

                ||

                "Không kết nối được máy chủ."

            );

        }
        finally {

            orderSubmitting =
                false;

            if (
                !createdPaymentOrder
            ) {

                setButtonLoading(

                    orderButton,

                    false,

                    "",

                    originalText

                );

            }

        }

    }
);


// =========================================================
// BANK TRANSFER MODAL
// =========================================================

function showBankTransferModal(
    order
) {

    if (
        !paymentModal
    ) {

        alert(
            "Đơn đã được tạo nhưng không mở được cửa sổ QR."
        );

        window.location.href =
            "/track-order";

        return;

    }


    if (
        paymentOrderCode
    ) {

        paymentOrderCode.textContent =
            order.orderCode
            ||
            "";

    }


    if (
        paymentAmount
    ) {

        paymentAmount.textContent =
            formatMoney(
                order.totalAmount
            );

    }


    if (
        paymentContent
    ) {

        paymentContent.textContent =
            order.orderCode
            ||
            "";

    }


    paymentModal.classList.add(
        "show"
    );

    document.body.classList.add(
        "payment-modal-open"
    );

}


// =========================================================
// CLOSE PAYMENT MODAL
// =========================================================

function closeBankTransferModal() {

    paymentModal?.classList.remove(
        "show"
    );

    document.body.classList.remove(
        "payment-modal-open"
    );

}


// =========================================================
// CLOSE X
// =========================================================

closePaymentModalButton?.addEventListener(
    "click",
    () => {

        closeBankTransferModal();

        window.location.href =
            "/track-order";

    }
);


// =========================================================
// PAY LATER
// =========================================================

payLaterButton?.addEventListener(
    "click",
    () => {

        closeBankTransferModal();

        window.location.href =
            "/track-order";

    }
);


// =========================================================
// CLICK MODAL BACKDROP
// =========================================================

paymentModal?.addEventListener(
    "click",
    (
        event
    ) => {

        if (
            event.target ===
            paymentModal
        ) {

            closeBankTransferModal();

            window.location.href =
                "/track-order";

        }

    }
);


// =========================================================
// CUSTOMER REPORT BANK TRANSFER
// =========================================================

confirmTransferButton?.addEventListener(
    "click",
    async () => {

        if (
            !createdPaymentOrder?.orderCode
            ||
            !createdPaymentOrder?.phone
        ) {

            alert(
                "Không tìm thấy thông tin đơn hàng vừa tạo."
            );

            return;

        }

        const originalText =
            confirmTransferButton.textContent;

        confirmTransferButton.disabled =
            true;

        confirmTransferButton.textContent =
            "ĐANG GHI NHẬN...";

        try {

            const response =
                await fetch(

                    `/api/orders/${encodeURIComponent(createdPaymentOrder.orderCode)}/payment-reported`,

                    {

                        method:
                            "POST",

                        headers: {

                            "Content-Type":
                                "application/json"

                        },

                        body:
                            JSON.stringify({

                                phone:
                                    createdPaymentOrder.phone

                            })

                    }

                );

            const data =
                await readJsonResponse(
                    response
                );

            if (
                !response.ok
                ||
                !data.success
            ) {

                throw new Error(

                    data.message

                    ||

                    "Không thể ghi nhận thông báo chuyển khoản."

                );

            }

            closeBankTransferModal();

            alert(

                "Đã ghi nhận bạn báo đã chuyển khoản. "

                +

                "Cửa hàng sẽ kiểm tra giao dịch trước khi xác nhận thanh toán."

            );

            window.location.href =
                "/track-order";

        }
        catch (
            error
        ) {

            console.error(
                "Report payment error:",
                error
            );

            alert(

                error.message

                ||

                "Không thể kết nối tới máy chủ."

            );

            confirmTransferButton.disabled =
                false;

            confirmTransferButton.textContent =
                originalText;

        }

    }
);


// =========================================================
// ESC CLOSE MODAL
// =========================================================

document.addEventListener(
    "keydown",
    (
        event
    ) => {

        if (
            event.key ===
            "Escape"
            &&
            paymentModal?.classList.contains(
                "show"
            )
        ) {

            closeBankTransferModal();

            window.location.href =
                "/track-order";

        }

    }
);


// =========================================================
// INITIALIZE
// =========================================================

refreshPaymentSelection();

renderCheckout();