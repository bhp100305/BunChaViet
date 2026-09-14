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



// ======================
// ADD PRODUCT
// ======================

document
.getElementById("btnAdd")
.addEventListener("click", () => {


    mode = "add";


    modalTitle.innerHTML =
        "➕ Thêm món ăn";


    form.reset();


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

form.addEventListener("submit", function(e){


    e.preventDefault();


    let url;


    if(mode === "add"){

        url = "/admin/products/add";

    }
    else{

        url =
        "/admin/products/edit/"
        + productID.value;

    }



    fetch(url, {

        method:"POST",

        body:new FormData(form)

    })

    .then(res => res.json())

    .then(data => {


        if(data.success){

            alert("Lưu thành công!");

            location.reload();

        }
        else{

            alert("Có lỗi xảy ra!");

        }


    });


});




// ======================
// DELETE PRODUCT
// ======================

document
.querySelectorAll(".delete-product")
.forEach(button => {


    button.addEventListener("click", () => {


        let id =
        button.dataset.id;



        if(!confirm("Bạn có chắc muốn xóa món này?")){

            return;

        }



        fetch(
            "/admin/products/delete/" + id,
            {
                method:"DELETE"
            }
        )

        .then(res => res.json())

        .then(data => {


            if(data.success){

                alert("Đã xóa!");

                location.reload();

            }


        });


    });


});