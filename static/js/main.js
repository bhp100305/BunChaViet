let products = [];

let cart = [];

let currentCategoryId = "all";

let visibleCount = 8;

const LOAD_STEP = 4;



// ======================================
// LOAD PRODUCTS
// ======================================

async function loadProducts() {

    try {

        const response = await fetch("/api/products");

        products = await response.json();


        applyCategoryFilter();


    } catch (error) {

        console.error(
            "Lỗi load sản phẩm:",
            error
        );

    }

}





// ======================================
// FILTER CATEGORY
// ======================================

function filterProducts(categoryId, button) {


    document
        .querySelectorAll(".tab-btn")
        .forEach(btn => {

            btn.classList.remove("active");

        });



    if (button) {

        button.classList.add("active");

    }



    currentCategoryId = categoryId;


    visibleCount = 8;


    applyCategoryFilter();

}





function applyCategoryFilter() {


    let result;



    if (currentCategoryId === "all") {

        result = products;

    }

    else {


        result = products.filter(product => {


            let category =
                product.categoryID ??
                product.categoryId ??
                product.category_id;



            return String(category)
                === String(currentCategoryId);


        });


    }



    displayProducts(result);


}







// ======================================
// DISPLAY PRODUCTS
// ======================================

function displayProducts(list) {


    const container =
        document.getElementById(
            "product-list"
        );



    const loadMore =
        document.getElementById(
            "load-more-btn"
        );



    if (!container) return;



    container.innerHTML = "";



    if (list.length === 0) {


        container.innerHTML = `

        <p class="empty-product">

            Không có sản phẩm

        </p>

        `;


        if (loadMore) {

            loadMore.style.display = "none";

        }


        return;

    }





    list
        .slice(0, visibleCount)
        .forEach(product => {


            const id =
                product.productID ??
                product.id;



            const name =
                product.productName ??
                product.name;



            container.innerHTML += `


        <div class="product-card">


            <img 
            src="/static/images/${product.image}"
            alt="${name}">



            <div class="product-info">


                <h3>
                    ${name}
                </h3>



                <p>
                    ${product.description ?? ""}
                </p>



                <div class="price">

                    ${formatMoney(product.price)}

                </div>



                <button 
                class="add-cart"
                onclick="addToCart(${id})">


                    🛒 Thêm vào giỏ


                </button>


            </div>


        </div>


        `;



        });





    if (loadMore) {


        if (visibleCount >= list.length) {

            loadMore.style.display =
                "none";

        }

        else {

            loadMore.style.display =
                "block";

        }

    }


}





// ======================================
// LOAD MORE BUTTON
// ======================================


document
    .addEventListener(
        "DOMContentLoaded",
        () => {


            const button =
                document.getElementById(
                    "load-more-btn"
                );



            if (button) {


                button.onclick = function () {


                    visibleCount += LOAD_STEP;


                    applyCategoryFilter();


                };


            }


        });







// ======================================
// CART
// ======================================


function addToCart(productId) {


    const product =
        products.find(
            p =>
                String(p.productID ?? p.id)
                === String(productId)
        );



    if (!product) return;




    const id =
        product.productID ??
        product.id;



    const name =
        product.productName ??
        product.name;




    const item =
        cart.find(
            p =>
                String(p.id)
                === String(id)
        );



    if (item) {


        item.quantity++;


    }


    else {


        cart.push({

            id: id,

            name: name,

            price: Number(product.price),

            image: product.image,

            quantity: 1

        });


    }




    updateCartCount();



    alert(
        "Đã thêm món vào giỏ hàng!"
    );


}







function updateCartCount() {


    const count =
        cart.reduce(
            (sum, item) =>
                sum + item.quantity,
            0
        );



    const element =
        document.getElementById(
            "cart-count"
        );



    if (element) {

        element.innerText = count;

    }


}







// ======================================
// SHOW CART
// ======================================


function showCart() {


    const box =
        document.getElementById(
            "cart-box"
        );


    const overlay =
        document.getElementById(
            "cart-overlay"
        );



    renderCart();



    box.classList.add(
        "active"
    );


    overlay.classList.add(
        "active"
    );


}






function closeCart() {


    document
        .getElementById(
            "cart-box"
        )
        .classList.remove(
            "active"
        );



    document
        .getElementById(
            "cart-overlay"
        )
        .classList.remove(
            "active"
        );


}







// ======================================
// RENDER CART
// ======================================


function renderCart() {


    const container =
        document.getElementById(
            "cart-items"
        );


    const totalBox =
        document.getElementById(
            "cart-total"
        );



    container.innerHTML = "";



    if (cart.length === 0) {


        container.innerHTML =
            `

        <p class="empty-cart">

            🛒 Giỏ hàng trống

        </p>

        `;


        totalBox.innerText =
            "0 ₫";


        return;

    }




    let total = 0;



    cart.forEach(item => {


        let money =
            item.price *
            item.quantity;



        total += money;




        container.innerHTML +=
            `


        <div class="cart-item">


            <img 
            src="/static/images/${item.image}">



            <div class="cart-item-info">


                <h4>
                    ${item.name}
                </h4>



                <p>
                    ${formatMoney(item.price)}
                </p>



                <div class="quantity">


                    <button onclick="decreaseQuantity(${item.id})">

                        -

                    </button>



                    <span>
                        ${item.quantity}
                    </span>



                    <button onclick="increaseQuantity(${item.id})">

                        +

                    </button>


                </div>


            </div>



            <div class="cart-item-right">


                <strong>
                    ${formatMoney(money)}
                </strong>



                <button
                class="remove-btn"
                onclick="removeFromCart(${item.id})">

                    Xóa

                </button>


            </div>


        </div>


        `;



    });




    totalBox.innerText =
        formatMoney(total);


}







function increaseQuantity(id) {


    const item =
        cart.find(
            x => String(x.id)
                === String(id)
        );


    if (item) {

        item.quantity++;

    }


    updateCartCount();

    renderCart();


}





function decreaseQuantity(id) {


    const item =
        cart.find(
            x => String(x.id)
                === String(id)
        );



    if (!item) return;



    item.quantity--;



    if (item.quantity <= 0) {

        removeFromCart(id);

        return;

    }


    updateCartCount();

    renderCart();


}






function removeFromCart(id) {


    cart =
        cart.filter(
            x =>
                String(x.id)
                !== String(id)
        );


    updateCartCount();

    renderCart();


}


// ======================================
// FORMAT MONEY
// ======================================


function formatMoney(number) {


    return Number(number)
        .toLocaleString("vi-VN")
        + " ₫";


}






// ======================================
// CHECKOUT
// ======================================


function goToCheckout() {

    if (cart.length === 0) {

        alert(
            "Giỏ hàng đang trống!"
        );

        return;

    }


    localStorage.setItem(
        "cart",
        JSON.stringify(cart)
    );


    window.location.href = "/checkout";

}






// START

loadProducts();