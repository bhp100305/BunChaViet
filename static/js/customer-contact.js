// =========================================================
// BUN CHA VIET - CONTACT
// =========================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        setupContactForm();

        setupOrderCodeField();

        setupMessageCounter();

        setupStoreMap();

    }
);


// =========================================================
// ELEMENTS
// =========================================================

function getContactElements() {

    return {

        form:
            document.getElementById(
                "contact-form"
            ),

        fullName:
            document.getElementById(
                "contact-fullname"
            ),

        phone:
            document.getElementById(
                "contact-phone"
            ),

        email:
            document.getElementById(
                "contact-email"
            ),

        subject:
            document.getElementById(
                "contact-subject"
            ),

        orderCode:
            document.getElementById(
                "contact-order-code"
            ),

        orderCodeField:
            document.getElementById(
                "order-code-field"
            ),

        message:
            document.getElementById(
                "contact-message"
            ),

        error:
            document.getElementById(
                "contact-error"
            ),

        success:
            document.getElementById(
                "contact-success"
            ),

        submit:
            document.getElementById(
                "contact-submit"
            ),

        sendAnother:
            document.getElementById(
                "send-another-contact"
            ),

        messageCount:
            document.getElementById(
                "message-count"
            ),

    };

}


// =========================================================
// SUBJECT / ORDER CODE
// =========================================================

function setupOrderCodeField() {

    const elements =
        getContactElements();


    if (
        !elements.subject
        ||
        !elements.orderCodeField
    ) {

        return;

    }


    function update() {

        const requiresOrder =
            elements.subject.value
            ===
            "Phản ánh đơn hàng";


        elements.orderCodeField
            .classList.toggle(
                "show",
                requiresOrder
            );


        if (
            elements.orderCode
        ) {

            elements.orderCode.required =
                requiresOrder;


            if (
                !requiresOrder
            ) {

                elements.orderCode.value =
                    "";

            }

        }

    }


    elements.subject.addEventListener(
        "change",
        update
    );


    update();

}


// =========================================================
// MESSAGE COUNTER
// =========================================================

function setupMessageCounter() {

    const elements =
        getContactElements();


    if (
        !elements.message
        ||
        !elements.messageCount
    ) {

        return;

    }


    function updateCounter() {

        elements.messageCount.textContent =
            String(
                elements.message.value.length
            );

    }


    elements.message.addEventListener(
        "input",
        updateCounter
    );


    updateCounter();

}


// =========================================================
// CONTACT FORM
// =========================================================

function setupContactForm() {

    const elements =
        getContactElements();


    if (
        !elements.form
    ) {

        return;

    }


    elements.form.addEventListener(
        "submit",
        async (
            event
        ) => {

            event.preventDefault();


            hideError(
                elements.error
            );


            const payload = {

                fullName:
                    elements.fullName?.value.trim()
                    ||
                    "",

                phone:
                    elements.phone?.value.trim()
                    ||
                    "",

                email:
                    elements.email?.value.trim()
                    ||
                    "",

                subject:
                    elements.subject?.value
                    ||
                    "",

                orderCode:
                    elements.orderCode?.value.trim().toUpperCase()
                    ||
                    "",

                message:
                    elements.message?.value.trim()
                    ||
                    "",

            };


            if (
                !validateContact(
                    payload,
                    elements
                )
            ) {

                return;

            }


            const oldText =
                elements.submit?.textContent
                ||
                "GỬI LIÊN HỆ";


            if (
                elements.submit
            ) {

                elements.submit.disabled =
                    true;


                elements.submit.textContent =
                    "ĐANG GỬI...";

            }


            try {

                const response =
                    await fetch(
                        "/api/contact",
                        {

                            method:
                                "POST",

                            headers: {

                                "Content-Type":
                                    "application/json",

                            },

                            body:
                                JSON.stringify(
                                    payload
                                ),

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

                        "Không thể gửi liên hệ."

                    );

                }


                showSuccess(
                    elements
                );

            }
            catch (
                error
            ) {

                console.error(
                    "Contact error:",
                    error
                );


                showError(

                    elements.error,

                    error.message
                    ||
                    "Không thể kết nối tới máy chủ."

                );

            }
            finally {

                if (
                    elements.submit
                ) {

                    elements.submit.disabled =
                        false;


                    elements.submit.textContent =
                        oldText;

                }

            }

        }
    );


    elements.sendAnother?.addEventListener(
        "click",
        () => {

            resetContactForm(
                elements
            );

        }
    );

}


// =========================================================
// VALIDATE
// =========================================================

function validateContact(
    payload,
    elements
) {

    if (
        !payload.fullName
    ) {

        showError(
            elements.error,
            "Vui lòng nhập họ và tên."
        );


        elements.fullName?.focus();


        return false;

    }


    if (
        !payload.phone
    ) {

        showError(
            elements.error,
            "Vui lòng nhập số điện thoại."
        );


        elements.phone?.focus();


        return false;

    }


    const phone =
        payload.phone
            .replace(
                /\s+/g,
                ""
            )
            .replace(
                /-/g,
                ""
            );


    if (
        !/^[0-9]{9,12}$/.test(
            phone
        )
    ) {

        showError(
            elements.error,
            "Số điện thoại không hợp lệ."
        );


        elements.phone?.focus();


        return false;

    }


    if (
        payload.email
        &&
        !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(
            payload.email
        )
    ) {

        showError(
            elements.error,
            "Email không hợp lệ."
        );


        elements.email?.focus();


        return false;

    }


    if (
        !payload.subject
    ) {

        showError(
            elements.error,
            "Vui lòng chọn chủ đề."
        );


        elements.subject?.focus();


        return false;

    }


    if (
        payload.subject
        ===
        "Phản ánh đơn hàng"
        &&
        !payload.orderCode
    ) {

        showError(
            elements.error,
            "Vui lòng nhập mã đơn hàng cần phản ánh."
        );


        elements.orderCode?.focus();


        return false;

    }


    if (
        !payload.message
    ) {

        showError(
            elements.error,
            "Vui lòng nhập nội dung liên hệ."
        );


        elements.message?.focus();


        return false;

    }


    return true;

}


// =========================================================
// SUCCESS
// =========================================================

function showSuccess(
    elements
) {

    elements.form?.classList.add(
        "hidden"
    );


    elements.success?.classList.add(
        "show"
    );


    elements.success?.scrollIntoView({

        behavior:
            "smooth",

        block:
            "center",

    });

}


// =========================================================
// RESET
// =========================================================

function resetContactForm(
    elements
) {

    elements.form?.reset();


    elements.success?.classList.remove(
        "show"
    );


    elements.form?.classList.remove(
        "hidden"
    );


    elements.orderCodeField?.classList.remove(
        "show"
    );


    if (
        elements.orderCode
    ) {

        elements.orderCode.required =
            false;

    }


    if (
        elements.messageCount
    ) {

        elements.messageCount.textContent =
            "0";

    }


    hideError(
        elements.error
    );


    elements.fullName?.focus();

}


// =========================================================
// ERROR
// =========================================================

function showError(
    element,
    message
) {

    if (!element) {

        return;

    }


    element.textContent =
        message;


    element.classList.add(
        "show"
    );

}


function hideError(
    element
) {

    if (!element) {

        return;

    }


    element.textContent =
        "";


    element.classList.remove(
        "show"
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
    catch (
        error
    ) {

        console.error(
            "Invalid JSON:",
            error
        );


        return {

            success:
                false,

            message:
                "Máy chủ trả về dữ liệu không hợp lệ.",

        };

    }

}


// =========================================================
// STORE MAP
// =========================================================

function setupStoreMap() {

    const mapElement =
        document.getElementById(
            "contact-map"
        );


    if (
        !mapElement
        ||
        typeof L ===
        "undefined"
    ) {

        return;

    }


    /*
     * Tọa độ đang dùng đồng bộ với checkout.
     *
     * Nếu địa chỉ cửa hàng thực tế khác,
     * đổi hai giá trị này.
     */

    const shopLat =
        21.0338;


    const shopLng =
        105.8019;


    const map =
        L.map(
            mapElement
        ).setView(
            [
                shopLat,
                shopLng,
            ],
            16
        );


    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {

            maxZoom:
                19,

            attribution:
                "&copy; OpenStreetMap",

        }
    ).addTo(
        map
    );


    const storeIcon =
        L.divIcon({

            className:
                "contact-store-marker-wrapper",

            html:
                `
                <div class="contact-store-marker">
                    🍜
                </div>
                `,

            iconSize:
                [
                    54,
                    54,
                ],

            iconAnchor:
                [
                    27,
                    27,
                ],

        });


    L.marker(
        [
            shopLat,
            shopLng,
        ],
        {

            icon:
                storeIcon,

        }
    )
        .addTo(
            map
        )
        .bindPopup(
            `
            <strong>Bún Chả Việt</strong>
            <br>
            Số 3 Cầu Giấy, Hà Nội
            <br>
            08:00 - 22:00
            `
        )
        .openPopup();

}