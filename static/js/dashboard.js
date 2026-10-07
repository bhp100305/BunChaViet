// =========================================================
// ADMIN DASHBOARD
// BUN CHA VIET
// =========================================================


document.addEventListener(
    "DOMContentLoaded",
    function () {

        setupClock();

        setupRefreshButton();

        setupMobileSidebar();

        setupRecentOrderRows();

    }
);


// =========================================================
// CLOCK
// =========================================================

function setupClock() {

    updateClock();

    window.setInterval(
        updateClock,
        1000
    );

}


// =========================================================
// UPDATE CLOCK
// =========================================================

function updateClock() {

    const clock =
        document.getElementById(
            "dashboardClock"
        );


    const dateElement =
        document.getElementById(
            "dashboardDate"
        );


    if (
        !clock ||
        !dateElement
    ) {

        return;

    }


    const now =
        new Date();


    clock.textContent =
        formatTwoDigits(
            now.getHours()
        )
        +
        ":"
        +
        formatTwoDigits(
            now.getMinutes()
        );


    dateElement.textContent =
        formatTwoDigits(
            now.getDate()
        )
        +
        "/"
        +
        formatTwoDigits(
            now.getMonth() + 1
        )
        +
        "/"
        +
        now.getFullYear();

}


// =========================================================
// TWO DIGITS
// =========================================================

function formatTwoDigits(
    value
) {

    return String(
        value
    ).padStart(
        2,
        "0"
    );

}


// =========================================================
// REFRESH BUTTON
// =========================================================

function setupRefreshButton() {

    const button =
        document.getElementById(
            "refreshDashboardBtn"
        );


    if (!button) {

        return;

    }


    button.addEventListener(
        "click",
        function () {

            if (
                button.classList.contains(
                    "loading"
                )
            ) {

                return;

            }


            button.classList.add(
                "loading"
            );


            button.disabled =
                true;


            const text =
                button.querySelector(
                    "span:last-child"
                );


            if (text) {

                text.textContent =
                    "Đang tải...";

            }


            setTimeout(
                function () {

                    window.location.reload();

                },
                250
            );

        }
    );

}


// =========================================================
// MOBILE SIDEBAR
// =========================================================

function setupMobileSidebar() {

    const sidebar =
        document.getElementById(
            "adminSidebar"
        );


    const button =
        document.getElementById(
            "mobileMenuBtn"
        );


    const overlay =
        document.getElementById(
            "sidebarOverlay"
        );


    if (
        !sidebar ||
        !button ||
        !overlay
    ) {

        return;

    }


    button.addEventListener(
        "click",
        function () {

            openSidebar(
                sidebar,
                overlay
            );

        }
    );


    overlay.addEventListener(
        "click",
        function () {

            closeSidebar(
                sidebar,
                overlay
            );

        }
    );


    const links =
        sidebar.querySelectorAll(
            "a"
        );


    links.forEach(
        function (link) {

            link.addEventListener(
                "click",
                function () {

                    if (
                        window.innerWidth
                        <=
                        980
                    ) {

                        closeSidebar(
                            sidebar,
                            overlay
                        );

                    }

                }
            );

        }
    );


    document.addEventListener(
        "keydown",
        function (event) {

            if (
                event.key ===
                "Escape"
            ) {

                closeSidebar(
                    sidebar,
                    overlay
                );

            }

        }
    );


    window.addEventListener(
        "resize",
        function () {

            if (
                window.innerWidth
                >
                980
            ) {

                closeSidebar(
                    sidebar,
                    overlay
                );

            }

        }
    );

}


// =========================================================
// OPEN SIDEBAR
// =========================================================

function openSidebar(
    sidebar,
    overlay
) {

    sidebar.classList.add(
        "mobile-open"
    );


    overlay.classList.add(
        "show"
    );


    document.body.style.overflow =
        "hidden";

}


// =========================================================
// CLOSE SIDEBAR
// =========================================================

function closeSidebar(
    sidebar,
    overlay
) {

    sidebar.classList.remove(
        "mobile-open"
    );


    overlay.classList.remove(
        "show"
    );


    document.body.style.overflow =
        "";

}


// =========================================================
// RECENT ORDER ROW
// =========================================================

function setupRecentOrderRows() {

    const rows =
        document.querySelectorAll(
            ".recent-order-row"
        );


    rows.forEach(
        function (row) {

            row.addEventListener(
                "click",
                function () {

                    const orderId =
                        row.dataset.orderId;


                    if (!orderId) {

                        window.location.href =
                            "/admin/orders";

                        return;

                    }


                    /*
                     * Hiện tại trang Orders chưa có
                     * route detail riêng.
                     *
                     * Vì vậy click sẽ mở danh sách
                     * quản lý đơn thay vì dựng URL
                     * giả rồi nhận 404 như một số
                     * dự án rất nhiệt tình vẫn làm.
                     */

                    window.location.href =
                        "/admin/orders";

                }
            );


            row.setAttribute(
                "tabindex",
                "0"
            );


            row.addEventListener(
                "keydown",
                function (event) {

                    if (
                        event.key === "Enter"
                        ||
                        event.key === " "
                    ) {

                        event.preventDefault();

                        row.click();

                    }

                }
            );

        }
    );

}