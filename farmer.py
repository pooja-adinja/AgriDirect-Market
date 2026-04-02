from flask import Blueprint, render_template, session, redirect, request
from db import get_db
from utils.notifications import create_notification

farmer_bp = Blueprint(
    "farmer",
    __name__,
    url_prefix="/farmer",
    template_folder="templates/farmer"
)

LOW_STOCK_THRESHOLD = 5


def farmer_only():
    return session.get("role") == "farmer"


# ============================
# DASHBOARD
# ============================
@farmer_bp.route("/dashboard")
def dashboard():
    if not farmer_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) AS total_products FROM products WHERE farmer_id=%s",
                (session["user_id"],))
    total_products = cur.fetchone()["total_products"]

    cur.execute("SELECT COUNT(*) AS total_orders FROM orders WHERE farmer_id=%s",
                (session["user_id"],))
    total_orders = cur.fetchone()["total_orders"]

    cur.execute("""
        SELECT IFNULL(SUM(total_amount),0) AS revenue
        FROM orders
        WHERE farmer_id=%s AND status='delivered'
    """, (session["user_id"],))
    revenue = cur.fetchone()["revenue"]

    return render_template(
        "farmer/dashboard.html",
        total_products=total_products,
        total_orders=total_orders,
        revenue=revenue
    )


# ============================
# PRODUCTS
# ============================
@farmer_bp.route("/products")
def products():
    if not farmer_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()
    cur.execute("""
        SELECT * FROM products
        WHERE farmer_id=%s
        ORDER BY created_at DESC
    """, (session["user_id"],))

    return render_template("products.html", products=cur.fetchall())


@farmer_bp.route("/products/create", methods=["POST"])
def create_product():
    if not farmer_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO products
        (farmer_id, title, description, price, quantity, category)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (
        session["user_id"],
        request.form["title"],
        request.form.get("description"),
        request.form["price"],
        request.form["quantity"],
        request.form["category"]
    ))

    return redirect("/farmer/products")


@farmer_bp.route("/products/update/<int:product_id>", methods=["POST"])
def update_product(product_id):
    if not farmer_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()

    cur.execute("""
        UPDATE products
        SET title=%s, description=%s, price=%s, category=%s
        WHERE id=%s AND farmer_id=%s
    """, (
        request.form["title"],
        request.form.get("description"),
        request.form["price"],
        request.form["category"],
        product_id,
        session["user_id"]
    ))

    return redirect("/farmer/products")



@farmer_bp.route("/products/toggle/<int:product_id>", methods=["GET"])
def activate_prod(product_id):
    if not farmer_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()

    cur.execute("""
        UPDATE products
        SET is_active = NOT is_active
        WHERE id=%s 
    """, (
        product_id,
    ))

    return redirect("/farmer/products")


@farmer_bp.route("/products/delete/<int:product_id>")
def delete_product(product_id):
    if not farmer_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()
    cur.execute("""
        DELETE FROM products
        WHERE id=%s AND farmer_id=%s
    """, (product_id, session["user_id"]))

    return redirect("/farmer/products")


# ============================
# INVENTORY + LOW STOCK ALERT
# ============================
@farmer_bp.route("/inventory")
def inventory():
    if not farmer_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()
    cur.execute("""
        SELECT id, title, quantity
        FROM products
        WHERE farmer_id=%s
    """, (session["user_id"],))

    return render_template("inventory.html", products=cur.fetchall())


@farmer_bp.route("/inventory/update", methods=["POST"])
def update_inventory():
    if not farmer_only():
        return redirect("/auth/login")

    product_id = request.form["product_id"]
    action = request.form["action"]
    qty = int(request.form["quantity"])
    remarks = request.form.get("remarks")

    con = get_db()
    cur = con.cursor()

    if action == "add":
        cur.execute("""
            UPDATE products SET quantity = quantity + %s
            WHERE id=%s AND farmer_id=%s
        """, (qty, product_id, session["user_id"]))

    elif action == "reduce":
        cur.execute("""
            UPDATE products SET quantity = GREATEST(quantity - %s, 0)
            WHERE id=%s AND farmer_id=%s
        """, (qty, product_id, session["user_id"]))

    elif action == "adjust":
        cur.execute("""
            UPDATE products SET quantity = %s
            WHERE id=%s AND farmer_id=%s
        """, (qty, product_id, session["user_id"]))

    # Inventory log
    cur.execute("""
        INSERT INTO inventory_logs
        (product_id, farmer_id, change_type, quantity, remarks)
        VALUES (%s,%s,%s,%s,%s)
    """, (product_id, session["user_id"], action, qty, remarks))

    # 🔔 LOW STOCK NOTIFICATION
    cur.execute("""
        SELECT title, quantity
        FROM products
        WHERE id=%s AND farmer_id=%s
    """, (product_id, session["user_id"]))

    product = cur.fetchone()

    if product and product["quantity"] <= LOW_STOCK_THRESHOLD:
        create_notification(
            session["user_id"],
            "Low Stock Alert",
            f"Product '{product['title']}' is low (Qty: {product['quantity']})",
            "stock"
        )

    return redirect("/farmer/inventory")


# ============================
# ORDERS + CUSTOMER NOTIFY
# ============================
@farmer_bp.route("/orders")
def farmer_orders():
    if not farmer_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()
    cur.execute("""
        SELECT o.*, u.name AS customer_name
        FROM orders o
        JOIN users u ON o.customer_id = u.id
        WHERE o.farmer_id=%s
        ORDER BY o.created_at DESC
    """, (session["user_id"],))

    return render_template("farmer/orders.html", orders=cur.fetchall())



@farmer_bp.route("/orders/update", methods=["POST"])
def update_order_status():
    if not farmer_only():
        return redirect("/auth/login")

    order_id = request.form["order_id"]
    action = request.form["action"]

    transitions = {
        "accept": ("pending", "accepted"),
        "reject": ("pending", "rejected"),
        "confirm": ("accepted", "confirmed"),
        "deliver": ("confirmed", "delivered"),
    }

    if action not in transitions:
        return redirect("/farmer/orders")

    expected, new_status = transitions[action]

    con = get_db()
    cur = con.cursor()

    cur.execute("""
        UPDATE orders
        SET status=%s, updated_at=NOW()
        WHERE id=%s AND farmer_id=%s AND status=%s
    """, (new_status, order_id, session["user_id"], expected))

    # 🔔 CUSTOMER NOTIFICATION
    cur.execute("""
        SELECT customer_id
        FROM orders
        WHERE id=%s AND farmer_id=%s
    """, (order_id, session["user_id"]))

    order = cur.fetchone()

    if order:
        create_notification(
            order["customer_id"],
            "Order Update",
            f"Your order #{order_id} is now {new_status}",
            "order"
        )

    return redirect("/farmer/orders")


# ============================
# TRANSACTIONS
# ============================
@farmer_bp.route("/transactions")
def transactions():
    if not farmer_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()
    cur.execute("""
        SELECT t.*, o.id AS order_no
        FROM transactions t
        JOIN orders o ON t.order_id = o.id
        WHERE t.farmer_id=%s
        ORDER BY t.created_at DESC
    """, (session["user_id"],))

    return render_template("transactions.html", transactions=cur.fetchall())
