// =====================================================
// ADMIN DASHBOARD JAVASCRIPT
// BÚN CHẢ VIỆT
// =====================================================



document.addEventListener(
    "DOMContentLoaded",
    function(){


        console.log(
            "Admin JS Loaded"
        );


        loadDashboard();



    }
);


function loadDashboard(){


    fetch("/admin/api/dashboard")

    .then(
        response => response.json()
    )


    .then(
        data => {


            console.log(
                data
            );


            if(data.success){


                updateDashboard(
                    data
                );


            }


        }

    )


    .catch(

        error => {

            console.error(
                "Dashboard error:",
                error
            );

        }

    );


}


function updateDashboard(data){



    const productCount =
    document.getElementById(
        "product-count"
    );



    const orderCount =
    document.getElementById(
        "order-count"
    );



    const userCount =
    document.getElementById(
        "user-count"
    );



    const categoryCount =
    document.getElementById(
        "category-count"
    );





    if(productCount)
        productCount.innerHTML =
        data.products;




    if(orderCount)
        orderCount.innerHTML =
        data.orders;




    if(userCount)
        userCount.innerHTML =
        data.users;




    if(categoryCount)
        categoryCount.innerHTML =
        data.categories;



}

function loadProducts(){



fetch("/admin/api/products")


.then(

response =>
response.json()

)


.then(

data => {


    renderProducts(
        data
    );


}


)

.catch(

error =>
console.log(error)

);


}






function renderProducts(products){


const box =
document.getElementById(
    "product-table"
);



if(!box)
return;



box.innerHTML="";



products.forEach(

product => {



box.innerHTML += `


<tr>


<td>
${product.id}
</td>


<td>

<img 
src="${product.image}"
width="60">

</td>


<td>
${product.name}
</td>


<td>
${product.price} đ
</td>


<td>

<button 
onclick="editProduct(${product.id})">

Sửa

</button>


<button
onclick="deleteProduct(${product.id})">

Xóa

</button>


</td>



</tr>


`;



}


);



}



function deleteProduct(id){



if(
!confirm(
"Bạn có chắc muốn xóa món này?"
)

)

return;

fetch(

"/admin/api/products/" + id,

{

method:"DELETE"

}

)


.then(

response =>
response.json()

)


.then(

data => {


alert(
data.message
);


loadProducts();


}


)





}


function editProduct(id){


window.location.href =

"/admin/products/edit/" + id;

}



function logout(){


if(
confirm(
"Bạn muốn đăng xuất?"
)

)

{

window.location.href="/logout";


}



}