// =========================================================
// ADMIN PAYMENT
// BUN CHA VIET
// =========================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        setupPaymentActions();

    }
);


// =========================================================
// ACTION BUTTONS
// =========================================================

function setupPaymentActions() {

    document
        .querySelectorAll(
            "[data-payment-action]"
        )
        .forEach(
            (
                button
            ) => {

                button.addEventListener(
                    "click",
                    async () => {

                        const orderId =
                            button.dataset.orderId;


                        const action =
                            button.dataset.paymentAction;


                        if (
                            !orderId
                            ||
                            !action
                        ) {

                            return;

                        }


                        let confirmMessage =
                            "Xác nhận thanh toán?";


                        if (
                            action
                            ===
                            "CONFIRM_PAID"
                        ) {

                            confirmMessage =
                                "Bạn đã kiểm tra tài khoản ngân hàng và xác nhận tiền đã được chuyển vào?";

                        }


                        if (
                            action
                            ===
                            "CONFIRM_CASH_COLLECTED"
                        ) {

                            confirmMessage =
                                "Xác nhận đơn hàng đã hoàn thành và đã thu đủ tiền mặt?";

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


                        button.textContent =
                            "Đang xử lý...";


                        try {

                            const response =
                                await fetch(

                                    `/admin/payments/${encodeURIComponent(orderId)}/confirm`,

                                    {

                                        method:
                                            "POST",

                                        credentials:
                                            "same-origin",

                                        headers: {

                                            "Content-Type":
                                                "application/json",

                                            "Accept":
                                                "application/json",

                                        },

                                        body:
                                            JSON.stringify({

                                                action:
                                                    action,

                                            }),

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

                                    "Không thể cập nhật thanh toán."

                                );

                            }


                            window.location.reload();

                        }
                        catch (
                            error
                        ) {

                            console.error(
                                "Payment error:",
                                error
                            );


                            alert(

                                error.message

                                ||

                                "Không thể kết nối tới máy chủ."

                            );


                            button.disabled =
                                false;


                            button.textContent =
                                oldText;

                        }

                    }
                );

            }
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
            "Invalid JSON:",
            error
        );


        return {

            success:
                false,

            message:
                "Server trả về dữ liệu không hợp lệ.",

        };

    }

}