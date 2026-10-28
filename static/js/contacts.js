// =========================================================
// ADMIN CONTACTS
// BUN CHA VIET
// =========================================================

let selectedContactId =
    null;


// =========================================================
// INIT
// =========================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        setupContactRows();

        setupContactModal();

        setupFilterStyle();

    }
);


// =========================================================
// CONTACT ROW
// =========================================================

function setupContactRows() {

    document
        .querySelectorAll(
            "[data-contact-id]"
        )
        .forEach(
            (button) => {

                button.addEventListener(
                    "click",
                    async () => {

                        const contactId =
                            Number(
                                button.dataset.contactId
                            );


                        if (
                            !Number.isInteger(
                                contactId
                            )
                        ) {

                            return;

                        }


                        await openContactModal(
                            contactId
                        );

                    }
                );

            }
        );

}


// =========================================================
// SETUP MODAL
// =========================================================

function setupContactModal() {

    const modal =
        document.getElementById(
            "contactDetailModal"
        );


    const closeButton =
        document.getElementById(
            "closeContactModal"
        );


    const cancelButton =
        document.getElementById(
            "cancelContactModal"
        );


    const saveButton =
        document.getElementById(
            "saveContactStatus"
        );


    const copyButton =
        document.getElementById(
            "copyContactOrderCode"
        );


    closeButton?.addEventListener(
        "click",
        closeContactModal
    );


    cancelButton?.addEventListener(
        "click",
        closeContactModal
    );


    saveButton?.addEventListener(
        "click",
        saveContactStatus
    );


    copyButton?.addEventListener(
        "click",
        copyOrderCode
    );


    modal?.addEventListener(
        "click",
        (
            event
        ) => {

            if (
                event.target
                ===
                modal
            ) {

                closeContactModal();

            }

        }
    );


    document.addEventListener(
        "keydown",
        (
            event
        ) => {

            if (
                event.key
                ===
                "Escape"
                &&
                modal?.classList.contains(
                    "show"
                )
            ) {

                closeContactModal();

            }

        }
    );

}


// =========================================================
// OPEN MODAL
// =========================================================

async function openContactModal(
    contactId
) {

    const modal =
        document.getElementById(
            "contactDetailModal"
        );


    if (!modal) {

        return;

    }


    selectedContactId =
        contactId;


    setModalLoading(
        true
    );


    modal.classList.add(
        "show"
    );


    document.body.classList.add(
        "modal-open"
    );


    try {

        const response =
            await fetch(
                `/admin/contacts/${encodeURIComponent(contactId)}`,
                {

                    method:
                        "GET",

                    credentials:
                        "same-origin",

                    headers: {

                        "Accept":
                            "application/json"

                    }

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

                "Không thể tải liên hệ."

            );

        }


        fillContactModal(
            data.contact
        );

    }
    catch (
        error
    ) {

        console.error(
            "Load contact error:",
            error
        );


        alert(

            error.message

            ||

            "Không thể tải liên hệ."

        );


        closeContactModal();

    }
    finally {

        setModalLoading(
            false
        );

    }

}


// =========================================================
// FILL MODAL
// =========================================================

function fillContactModal(
    contact
) {

    setText(
        "detailContactId",
        `#${contact.id}`
    );


    setText(
        "detailFullName",
        contact.fullName
        ||
        "-"
    );


    setText(
        "detailPhone",
        contact.phone
        ||
        "-"
    );


    setText(
        "detailEmail",
        contact.email
        ||
        "Không cung cấp"
    );


    setText(
        "detailSubject",
        contact.subject
        ||
        "-"
    );


    setText(
        "detailCreatedAt",
        contact.createdAt
        ||
        "-"
    );


    setText(
        "detailUpdatedAt",
        contact.updatedAt
        ||
        "Chưa cập nhật"
    );


    setText(
        "detailResolvedAt",
        contact.resolvedAt
        ||
        "Chưa hoàn tất"
    );


    setText(
        "detailMessage",
        contact.message
        ||
        "-"
    );


    // =====================================================
    // STATUS
    // =====================================================

    const statusSelect =
        document.getElementById(
            "detailStatus"
        );


    if (
        statusSelect
    ) {

        statusSelect.value =
            contact.status
            ||
            "Mới";

    }


    // =====================================================
    // ADMIN NOTE
    // =====================================================

    const adminNote =
        document.getElementById(
            "detailAdminNote"
        );


    if (
        adminNote
    ) {

        adminNote.value =
            contact.adminNote
            ||
            "";

    }


    // =====================================================
    // ORDER
    // =====================================================

    const orderBox =
        document.getElementById(
            "detailOrderBox"
        );


    const orderCode =
        document.getElementById(
            "detailOrderCode"
        );


    if (
        contact.orderCode
    ) {

        orderBox?.classList.add(
            "show"
        );


        if (
            orderCode
        ) {

            orderCode.textContent =
                contact.orderCode;


            orderCode.dataset.orderCode =
                contact.orderCode;

        }


        setText(
            "detailOrderStatus",
            contact.orderStatus
            ||
            "Không xác định"
        );


        setText(
            "detailOrderAmount",
            formatMoney(
                contact.finalMoney
            )
        );

    }
    else {

        orderBox?.classList.remove(
            "show"
        );


        if (
            orderCode
        ) {

            orderCode.textContent =
                "";


            delete (
                orderCode.dataset.orderCode
            );

        }

    }

}


// =========================================================
// SAVE STATUS
// =========================================================

async function saveContactStatus() {

    if (
        !selectedContactId
    ) {

        return;

    }


    const statusSelect =
        document.getElementById(
            "detailStatus"
        );


    const adminNote =
        document.getElementById(
            "detailAdminNote"
        );


    const saveButton =
        document.getElementById(
            "saveContactStatus"
        );


    const status =
        statusSelect?.value
        ||
        "";


    const note =
        adminNote?.value.trim()
        ||
        "";


    if (
        ![
            "Mới",
            "Đang xử lý",
            "Đã phản hồi"
        ].includes(
            status
        )
    ) {

        alert(
            "Trạng thái không hợp lệ."
        );


        return;

    }


    const oldText =
        saveButton?.textContent
        ||
        "Lưu thay đổi";


    if (
        saveButton
    ) {

        saveButton.disabled =
            true;


        saveButton.textContent =
            "Đang lưu...";

    }


    try {

        const response =
            await fetch(

                `/admin/contacts/${encodeURIComponent(selectedContactId)}/status`,

                {

                    method:
                        "POST",

                    credentials:
                        "same-origin",

                    headers: {

                        "Content-Type":
                            "application/json",

                        "Accept":
                            "application/json"

                    },

                    body:
                        JSON.stringify({

                            status:
                                status,

                            adminNote:
                                note

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

                "Không thể cập nhật liên hệ."

            );

        }


        closeContactModal();


        window.location.reload();

    }
    catch (
        error
    ) {

        console.error(
            "Update contact error:",
            error
        );


        alert(

            error.message

            ||

            "Không thể cập nhật liên hệ."

        );


        if (
            saveButton
        ) {

            saveButton.disabled =
                false;


            saveButton.textContent =
                oldText;

        }

    }

}


// =========================================================
// CLOSE MODAL
// =========================================================

function closeContactModal() {

    const modal =
        document.getElementById(
            "contactDetailModal"
        );


    modal?.classList.remove(
        "show"
    );


    document.body.classList.remove(
        "modal-open"
    );


    selectedContactId =
        null;

}


// =========================================================
// LOADING
// =========================================================

function setModalLoading(
    loading
) {

    const content =
        document.getElementById(
            "contactModalContent"
        );


    const loadingElement =
        document.getElementById(
            "contactModalLoading"
        );


    content?.classList.toggle(
        "hidden",
        loading
    );


    loadingElement?.classList.toggle(
        "show",
        loading
    );

}


// =========================================================
// COPY ORDER CODE
// =========================================================

async function copyOrderCode() {

    const element =
        document.getElementById(
            "detailOrderCode"
        );


    const code =
        element?.dataset.orderCode
        ||
        "";


    if (!code) {

        return;

    }


    try {

        await navigator.clipboard.writeText(
            code
        );


        alert(
            `Đã sao chép mã đơn ${code}.`
        );

    }
    catch (
        error
    ) {

        console.warn(
            "Clipboard error:",
            error
        );


        alert(
            `Mã đơn: ${code}`
        );

    }

}


// =========================================================
// FILTER STYLE
// =========================================================

function setupFilterStyle() {

    document
        .querySelectorAll(
            ".contact-filter-select"
        )
        .forEach(
            (
                select
            ) => {

                function update() {

                    select.classList.toggle(

                        "has-value",

                        Boolean(
                            select.value
                        )

                    );

                }


                select.addEventListener(
                    "change",
                    update
                );


                update();

            }
        );

}


// =========================================================
// SET TEXT
// =========================================================

function setText(
    id,
    value
) {

    const element =
        document.getElementById(
            id
        );


    if (
        element
    ) {

        element.textContent =
            value;

    }

}


// =========================================================
// MONEY
// =========================================================

function formatMoney(
    value
) {

    return (

        (
            Number(
                value
            )
            ||
            0
        ).toLocaleString(
            "vi-VN"
        )

        +

        " ₫"

    );

}


// =========================================================
// JSON
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
            "Response không phải JSON:",
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