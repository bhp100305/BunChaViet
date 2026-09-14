from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    jsonify,
    request
)

from database import get_connection


shipper_bp = Blueprint(
    "shipper",
    __name__,
    url_prefix="/shipper"
)



def check_shipper():

    return session.get("role") == "Shipper"




@shipper_bp.route("/orders")
def orders():


    if not check_shipper():

        return redirect(
            url_for("login")
        )


    conn = get_connection()

    cursor = conn.cursor()



    cursor.execute("""
        SELECT *

        FROM Orders

        WHERE DriverID=?

        ORDER BY OrderID DESC

    """,
    (
        session.get("user_id"),
    ))



    orders = cursor.fetchall()



    cursor.close()

    conn.close()



    return render_template(
        "shipper/orders.html",
        orders=orders,
        username=session.get("fullname")
    )





@shipper_bp.route(
"/update/<int:id>",
methods=["POST"]
)

def update_status(id):


    if not check_shipper():

        return jsonify({
            "success":False
        })



    data=request.json


    conn=get_connection()

    cursor=conn.cursor()



    cursor.execute("""
        UPDATE Orders

        SET Status=?

        WHERE OrderID=?

    """,
    (
        data["status"],
        id
    ))



    conn.commit()


    cursor.close()

    conn.close()



    return jsonify({

        "success":True

    })