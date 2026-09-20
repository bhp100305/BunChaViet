// =========================================================
// GỬI VỊ TRÍ GPS CỦA SHIPPER
// =========================================================

function sendLocation(position) {

    const latitude =
        position.coords.latitude;

    const longitude =
        position.coords.longitude;


    fetch("/shipper/location", {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify({

            latitude: latitude,

            longitude: longitude

        })

    })
    .then(response => response.json())
    .then(data => {

        if (data.success) {

            console.log(
                "GPS đã cập nhật:",
                latitude,
                longitude
            );

        }

    })
    .catch(error => {

        console.error(
            "Lỗi gửi GPS:",
            error
        );

    });
}


// =========================================================
// LỖI GPS
// =========================================================

function locationError(error) {

    console.error(
        "Không lấy được vị trí:",
        error
    );

}


// =========================================================
// BẮT ĐẦU THEO DÕI GPS
// =========================================================

function startTrackingLocation() {

    if (!navigator.geolocation) {

        alert(
            "Điện thoại không hỗ trợ GPS!"
        );

        return;
    }


    navigator.geolocation.watchPosition(

        sendLocation,

        locationError,

        {
            enableHighAccuracy: true,

            maximumAge: 5000,

            timeout: 10000
        }

    );

}


document.addEventListener(
    "DOMContentLoaded",
    function() {

        startTrackingLocation();

    }
);

// =========================================================
// UPDATE ORDER STATUS
// =========================================================

document
.querySelectorAll(".status-btn")
.forEach(button => {


    button.onclick = async function(){


        const orderId =
            this.dataset.id;


        const status =
            this.dataset.status;



        try {


            const response =
                await fetch(

                    "/shipper/update/" + orderId,

                    {

                        method:"POST",

                        headers:{
                            "Content-Type":
                            "application/json"
                        },

                        body:
                        JSON.stringify({

                            status: status

                        })

                    }

                );



            const data =
                await response.json();



            if(data.success){


                alert(
                    "Cập nhật thành công!"
                );


                location.reload();


            }
            else{


                alert(
                    data.message ||
                    "Không thể cập nhật!"
                );


            }


        }
        catch(error){


            console.error(error);


            alert(
                "Lỗi kết nối server!"
            );


        }


    };


});