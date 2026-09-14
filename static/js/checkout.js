// =======================================
// CART
// =======================================

let cart = JSON.parse(
    localStorage.getItem("cart")
) || [];


// =======================================
// HIỂN THỊ ĐƠN HÀNG
// =======================================

function renderCheckout() {

    const box = document.getElementById(
        "checkout-items"
    );

    const totalElement = document.getElementById(
        "checkout-total"
    );


    box.innerHTML = "";

    let total = 0;


    cart.forEach(item => {


        const itemTotal =
            item.price * item.quantity;


        total += itemTotal;


        box.innerHTML += `

            <div class="checkout-item">

                <img 
                src="/static/images/${item.image}">


                <div>

                    <h3>
                        ${item.name}
                    </h3>


                    <p>
                        ${item.quantity}
                        x
                        ${formatMoney(item.price)}
                    </p>

                </div>


                <strong>
                    ${formatMoney(itemTotal)}
                </strong>


            </div>

        `;

    });


    totalElement.innerText =
        formatMoney(total);

}



// =======================================
// LOAD ĐỊA CHỈ VIỆT NAM
// API:
// https://provinces.open-api.vn/api/
// =======================================


const province =
    document.getElementById("province");


const district =
    document.getElementById("district");


const ward =
    document.getElementById("ward");




// LOAD TỈNH

async function loadProvince() {


    const response =
        await fetch(
            "https://provinces.open-api.vn/api/?depth=1"
        );


    const data =
        await response.json();



    data.forEach(item => {


        province.innerHTML += `

            <option value="${item.code}">
                ${item.name}
            </option>

        `;


    });


}




// CHỌN TỈNH -> HUYỆN

province.addEventListener(
    "change",
    async function () {


        district.innerHTML = `

            <option value="">
                Chọn quận/huyện
            </option>

        `;


        ward.innerHTML = `

            <option value="">
                Chọn phường/xã
            </option>

        `;



        const response =
            await fetch(

                "https://provinces.open-api.vn/api/p/"
                +
                this.value
                +
                "?depth=2"

            );



        const data =
            await response.json();



        data.districts.forEach(item => {


            district.innerHTML += `

                <option value="${item.code}">
                    ${item.name}
                </option>

            `;


        });


    }
);




// CHỌN HUYỆN -> XÃ

district.addEventListener(
    "change",
    async function () {


        ward.innerHTML = `

            <option value="">
                Chọn phường/xã
            </option>

        `;



        const response =
            await fetch(

                "https://provinces.open-api.vn/api/d/"
                +
                this.value
                +
                "?depth=2"

            );



        const data =
            await response.json();



        data.wards.forEach(item => {


            ward.innerHTML += `

                <option>
                    ${item.name}
                </option>

            `;


        });


    }
);




// =======================================
// ĐẶT HÀNG
// =======================================


document
.getElementById("order-btn")
.onclick = async function () {



    const fullname =
        document
        .getElementById("fullname")
        .value
        .trim();



    const phone =
        document
        .getElementById("phone")
        .value
        .trim();



    const address =
        document
        .getElementById("address")
        .value
        .trim();




    // CHECK DỮ LIỆU


    if(!fullname){

        alert(
            "Vui lòng nhập họ tên!"
        );

        return;

    }



    if(!phone){

        alert(
            "Vui lòng nhập số điện thoại!"
        );

        return;

    }



    if(!province.value){

        alert(
            "Vui lòng chọn tỉnh/thành phố!"
        );

        return;

    }



    if(!district.value){

        alert(
            "Vui lòng chọn quận/huyện!"
        );

        return;

    }



    if(!ward.value){

        alert(
            "Vui lòng chọn phường/xã!"
        );

        return;

    }



    if(!address){

        alert(
            "Vui lòng nhập địa chỉ cụ thể!"
        );

        return;

    }




    // TẠO ORDER


    const order = {


        customerName:
            fullname,


        phone:
            phone,


        province:
            province.options[
                province.selectedIndex
            ].text,


        district:
            district.options[
                district.selectedIndex
            ].text,


        ward:
            ward.options[
                ward.selectedIndex
            ].text,


        address:
            address,


        note:
            document
            .getElementById("note")
            .value
            .trim(),


        products:
            cart


    };





    try {


        const response =
            await fetch(
                "/api/orders",
                {

                    method:"POST",


                    headers:{
                        "Content-Type":
                        "application/json"
                    },


                    body:
                    JSON.stringify(order)

                }
            );



        const data =
            await response.json();




        if(data.success){


            // lưu mã đơn

            localStorage.setItem(
                "orderCode",
                data.orderCode
            );



            // chuyển sang trang theo dõi

            window.location.href =
                "/track-order";


        }
        else{


            alert(
                "Đặt hàng thất bại!"
            );


        }



    }
    catch(error){


        console.error(error);


        alert(
            "Không thể kết nối máy chủ!"
        );


    }


};




// =======================================
// FORMAT TIỀN
// =======================================


function formatMoney(price){

    return Number(price)
        .toLocaleString("vi-VN")
        +
        " ₫";

}




// =======================================
// START
// =======================================


renderCheckout();

loadProvince();