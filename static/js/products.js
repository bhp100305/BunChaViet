console.log("Product Admin Loaded");


let mode = "add";


const modal = document.getElementById("productModal");

const form = document.getElementById("productForm");

const modalTitle = document.getElementById("modalTitle");

const productID = document.getElementById("productID");

const productName = document.getElementById("productName");

const description = document.getElementById("description");

const price = document.getElementById("price");

const category = document.getElementById("category");
const formMessage = document.getElementById("productFormMessage");

function showProductFormMessage(message) {
    if (!formMessage) return;
    formMessage.textContent = message;
    formMessage.hidden = !message;
}



// ======================
// ADD PRODUCT
// ======================

document
.getElementById("btnAdd")
?.addEventListener("click", () => {


    mode = "add";


    modalTitle.innerHTML =
        "➕ Thêm món ăn";


    form.reset();
    showProductFormMessage("");


    productID.value = "";


    modal.style.display = "flex";

});




// ======================
// EDIT PRODUCT
// ======================

document
.querySelectorAll(".edit-product")
.forEach(button => {


    button.addEventListener("click", () => {


        mode = "edit";
        showProductFormMessage("");


        modalTitle.innerHTML =
            "✏ Sửa món ăn";


        productID.value =
            button.dataset.id;


        productName.value =
            button.dataset.name;


        description.value =
            button.dataset.description;


        price.value =
            button.dataset.price;


        category.value =
            button.dataset.category;


        modal.style.display = "flex";


    });


});




// ======================
// CLOSE MODAL
// ======================

document
.getElementById("btnClose")
.addEventListener("click", () => {

    modal.style.display = "none";

});



window.onclick = function(event){

    if(event.target === modal){

        modal.style.display = "none";

    }

};




// ======================
// SAVE PRODUCT
// ======================

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    showProductFormMessage("");

    const url = mode === "add"
        ? "/admin/products/add"
        : `/admin/products/edit/${productID.value}`;
    const submitButton = form.querySelector('[type="submit"]');
    if (submitButton) submitButton.disabled = true;

    try {
        const response = await fetch(url, {
            method: "POST",
            body: new FormData(form),
            credentials: "same-origin",
        });
        const data = await response.json();

        if (!response.ok || !data.success) {
            showProductFormMessage(data.message || "Không thể lưu sản phẩm.");
            return;
        }

        alert("Lưu thành công!");
        location.reload();
    } catch (error) {
        showProductFormMessage("Không thể kết nối máy chủ. Vui lòng thử lại.");
    } finally {
        if (submitButton) submitButton.disabled = false;
    }
});




async function sendProductAction(url, body = undefined) {
    const response = await fetch(url, {
        method: "POST",
        headers: body ? { "Content-Type": "application/json" } : {},
        body: body ? JSON.stringify(body) : undefined,
        credentials: "same-origin",
    });
    const data = await response.json();
    if (!response.ok || !data.success) {
        throw new Error(data.message || "Không thể cập nhật món ăn.");
    }
    location.reload();
}

document.querySelectorAll(".toggle-stock").forEach((button) => {
    button.addEventListener("click", async () => {
        const makeAvailable = button.dataset.available !== "1";
        const message = makeAvailable
            ? "Đưa món này trở lại trạng thái còn hàng?"
            : "Đánh dấu món này đã hết hàng? Món sẽ hiện mờ trên trang chủ và khách không thể đặt.";
        if (!window.confirm(message)) return;
        try {
            await sendProductAction(
                `/admin/products/availability/${button.dataset.id}`,
                { isAvailable: makeAvailable }
            );
        } catch (error) {
            window.alert(error.message);
        }
    });
});

document.querySelectorAll(".archive-product").forEach((button) => {
    button.addEventListener("click", async () => {
        if (!window.confirm("Lưu trữ món này? Món sẽ được ẩn khỏi trang chủ; dữ liệu đơn hàng cũ vẫn được giữ.")) return;
        try {
            await sendProductAction(`/admin/products/archive/${button.dataset.id}`);
        } catch (error) {
            window.alert(error.message);
        }
    });
});

document.querySelectorAll(".restore-product").forEach((button) => {
    button.addEventListener("click", async () => {
        if (!window.confirm("Khôi phục món này về danh sách kinh doanh?")) return;
        try {
            await sendProductAction(`/admin/products/restore/${button.dataset.id}`);
        } catch (error) {
            window.alert(error.message);
        }
    });
});
