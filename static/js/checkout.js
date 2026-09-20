// =====================================================
// CART + SHIPPING CONFIG
// =====================================================

let cart =
    JSON.parse(localStorage.getItem("cart")) || [];


let shippingFee = 0;


// Tọa độ cửa hàng
// Số 3 Cầu Giấy

const SHOP_LAT = 21.0338;

const SHOP_LNG = 105.8019;



// =====================================================
// RENDER CART
// =====================================================

function renderCheckout() {


    const box =
        document.getElementById(
            "checkout-items"
        );


    const foodTotal =
        document.getElementById(
            "food-total"
        );


    const totalBox =
        document.getElementById(
            "checkout-total"
        );


    let total = 0;


    box.innerHTML = "";



    cart.forEach(item => {


        const money =
            item.price * item.quantity;


        total += money;


        box.innerHTML += `

        <div class="checkout-item">

            <img src="/static/images/${item.image}">


            <div>

                <b>${item.name}</b>

                <p>
                ${item.quantity} x 
                ${item.price.toLocaleString()} ₫
                </p>

            </div>


            <strong>
            ${money.toLocaleString()} ₫
            </strong>

        </div>

        `;


    });



    // tiền món

    foodTotal.innerText =
        total.toLocaleString()
        +
        " ₫";



    // tổng cuối

    totalBox.innerText =
        (
            total + shippingFee
        )
        .toLocaleString()
        +
        " ₫";
        

}



renderCheckout();



// =====================================================
// MAP INITIALIZE
// =====================================================


const map =
    L.map("map")
    .setView(
        [
            21.0285,
            105.8542
        ],
        13
    );



L.tileLayer(
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
)
.addTo(map);



let marker = null;




// =====================================================
// SET LOCATION MARKER
// =====================================================


async function setMarker(
    lat,
    lng
) {


    if(marker) {

        map.removeLayer(marker);

    }



    marker =
        L.marker(
            [
                lat,
                lng
            ]
        )
        .addTo(map);



    map.setView(
        [
            lat,
            lng
        ],
        16
    );



    document
    .getElementById("latitude")
    .value = lat;



    document
    .getElementById("longitude")
    .value = lng;



    calculateShipping(
        lat,
        lng
    );



    await reverseGeocode(
        lat,
        lng
    );

}



// =====================================================
// CALCULATE DISTANCE
// =====================================================


function calculateDistance(
    lat1,
    lon1,
    lat2,
    lon2
) {


    const R = 6371;


    const dLat =
        (lat2 - lat1)
        *
        Math.PI
        /
        180;


    const dLon =
        (lon2 - lon1)
        *
        Math.PI
        /
        180;



    const a =

        Math.sin(dLat / 2)
        *
        Math.sin(dLat / 2)

        +

        Math.cos(
            lat1 * Math.PI / 180
        )

        *

        Math.cos(
            lat2 * Math.PI / 180
        )

        *

        Math.sin(dLon / 2)
        *
        Math.sin(dLon / 2);



    const c =
        2 *
        Math.atan2(
            Math.sqrt(a),
            Math.sqrt(1 - a)
        );



    return R * c;

}




// =====================================================
// SHIPPING FEE
// =====================================================


function calculateShippingFee(
    distance
) {


    if(distance <= 2) {

        return 10000;

    }


    if(distance <= 5) {

        return 15000;

    }


    if(distance <= 10) {

        return 25000;

    }


    return 50000;

}




function calculateShipping(
    lat,
    lng
) {


    const distance =
        calculateDistance(
            SHOP_LAT,
            SHOP_LNG,
            Number(lat),
            Number(lng)
        );



    shippingFee =
        calculateShippingFee(
            distance
        );



    document
    .getElementById("distance")
    .innerText =
        distance.toFixed(1)
        +
        " km";



    document
    .getElementById("shipping-fee")
    .innerText =
        shippingFee.toLocaleString()
        +
        " ₫";
        renderCheckout();
}





// =====================================================
// REVERSE GEOCODE
// COORDINATE -> ADDRESS
// =====================================================


async function reverseGeocode(
    lat,
    lng
) {


    try {


        const response =
            await fetch(

            `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&accept-language=vi`

            );


        const data =
            await response.json();



        if(data.display_name) {


            document
            .getElementById("address")
            .value =
            data.display_name;


        }


    }
    catch(error) {


        console.log(
            error
        );

    }

}


// =====================================================
// ADDRESS AUTOCOMPLETE
// =====================================================


const addressInput =
    document.getElementById(
        "address"
    );


const suggestionBox =
    document.getElementById(
        "suggestions"
    );



let typingTimer;



addressInput.addEventListener(
    "input",
    function() {


        clearTimeout(
            typingTimer
        );



        const keyword =
            this.value.trim();



        if(keyword.length < 3) {


            suggestionBox.innerHTML =
                "";


            return;

        }



        typingTimer =
            setTimeout(

                () => searchAddress(keyword),

                500

            );


    }
);


async function searchAddress(
    keyword
) {


    const response =
        await fetch(

        `https://nominatim.openstreetmap.org/search?format=json&limit=5&countrycodes=vn&q=${encodeURIComponent(keyword)}`

        );



    const data =
        await response.json();



    suggestionBox.innerHTML =
        "";



    data.forEach(place => {


        const item =
            document.createElement(
                "div"
            );


        item.className =
            "suggestion-item";



        item.innerHTML =

            `
            📍 ${place.display_name}
            `;



        item.onclick = function() {


            addressInput.value =
                place.display_name;



            setMarker(
                place.lat,
                place.lon
            );



            suggestionBox.innerHTML =
                "";


        };



        suggestionBox.appendChild(
            item
        );


    });


}


// =====================================================
// CLICK MAP
// =====================================================


map.on(
    "click",
    function(e) {


        setMarker(

            e.latlng.lat,

            e.latlng.lng

        );


    }
);





// =====================================================
// CURRENT LOCATION
// =====================================================


document
.getElementById(
    "current-location"
)
.onclick = function() {



    navigator.geolocation.getCurrentPosition(

        function(position) {


            setMarker(

                position.coords.latitude,

                position.coords.longitude

            );


        },


        function() {


            alert(
                "Không lấy được vị trí"
            );


        }


    );


};





// =====================================================
// CREATE ORDER
// =====================================================


document
.getElementById(
    "order-btn"
)
.onclick = async function() {



    const order = {


        customerName:

            document
            .getElementById("fullname")
            .value
            .trim(),



        phone:

            document
            .getElementById("phone")
            .value
            .trim(),



        address:

            document
            .getElementById("address")
            .value
            .trim(),



        latitude:

            document
            .getElementById("latitude")
            .value,



        longitude:

            document
            .getElementById("longitude")
            .value,



        note:

            document
            .getElementById("note")
            .value
            .trim(),



        shippingFee,


        products: cart


    };




    if(!order.customerName) {


        alert(
            "Vui lòng nhập họ tên"
        );


        return;

    }



    if(!order.phone) {


        alert(
            "Vui lòng nhập số điện thoại"
        );


        return;

    }



    if(!order.latitude) {


        alert(
            "Vui lòng chọn vị trí giao hàng"
        );


        return;

    }




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



        if(data.success) {


            localStorage.setItem(
                "orderCode",
                data.orderCode
            );



            window.location.href =
                "/track-order";


        }
        else {


            alert(
                "Đặt hàng thất bại"
            );


        }


    }
    catch(error) {


        console.error(
            error
        );


        alert(
            "Không kết nối được server"
        );


    }


};