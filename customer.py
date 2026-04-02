from flask import Blueprint, render_template, session, redirect, request
from db import get_db

customer_bp = Blueprint(
    "customer",
    __name__,
    url_prefix="/customer"
)

def customer_only():
    return session.get("role") == "customer"


# ============================
# VIEW PRODUCTS (SEARCH / FILTER / SORT)
# ============================
@customer_bp.route("/dashboard")
def dashboard():
    if not customer_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()

    # Total orders
    cur.execute("""
        SELECT COUNT(*) AS total_orders
        FROM orders
        WHERE customer_id=%s
    """, (session["user_id"],))
    total_orders = cur.fetchone()["total_orders"]

    # Total spending (accepted / delivered)
    cur.execute("""
        SELECT IFNULL(SUM(total_amount),0) AS total_spent
        FROM orders
        WHERE customer_id=%s AND status IN ('accepted','delivered')
    """, (session["user_id"],))
    total_spent = cur.fetchone()["total_spent"]

    # Cart items
    cur.execute("""
        SELECT COUNT(*) AS cart_items
        FROM cart
        WHERE customer_id=%s
    """, (session["user_id"],))
    cart_items = cur.fetchone()["cart_items"]

    # Complaints count
    cur.execute("""
        SELECT COUNT(*) AS complaints
        FROM complaints
        WHERE user_id=%s
    """, (session["user_id"],))
    complaints = cur.fetchone()["complaints"]

    return render_template(
        "customer/dashboard.html",
        total_orders=total_orders,
        total_spent=total_spent,
        cart_items=cart_items,
        complaints=complaints
    )

@customer_bp.route("/products")
def products():
    if not customer_only():
        return redirect("/auth/login")

    search = request.args.get("search", "")
    category = request.args.get("category", "")
    sort = request.args.get("sort", "")

    query = """
        SELECT p.*, u.name AS farmer_name,
               IFNULL(AVG(r.rating),0) AS avg_rating
        FROM products p
        JOIN users u ON p.farmer_id = u.id
        LEFT JOIN reviews r ON p.id = r.product_id
        WHERE p.is_active = 1
    """
    params = []

    if search:
        query += " AND p.title LIKE %s"
        params.append(f"%{search}%")

    if category:
        query += " AND p.category = %s"
        params.append(category)

    query += " GROUP BY p.id"

    if sort == "price_low":
        query += " ORDER BY p.price ASC"
    elif sort == "price_high":
        query += " ORDER BY p.price DESC"
    elif sort == "rating":
        query += " ORDER BY avg_rating DESC"

    con = get_db()
    cur = con.cursor()
    cur.execute(query, params)
    products = cur.fetchall()

    # ✅ IMPORTANT FIX HERE
    return render_template("customer/products.html", products=products)


# ============================
# ADD REVIEW
# ============================
@customer_bp.route("/review/add", methods=["POST"])
def add_review():
    if not customer_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO reviews (product_id, customer_id, rating, comment)
        VALUES (%s, %s, %s, %s)
    """, (
        request.form["product_id"],
        session["user_id"],
        request.form["rating"],
        request.form["comment"]
    ))

    return redirect("/customer/products")


# ============================
# ADD TO CART
# ============================
@customer_bp.route("/cart/add", methods=["POST"])
def add_to_cart():
    if not customer_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO cart (customer_id, product_id, quantity)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE quantity = quantity + %s
    """, (
        session["user_id"],
        request.form["product_id"],
        request.form["quantity"],
        request.form["quantity"]
    ))

    return redirect("/customer/cart")


# ============================
# VIEW CART
# ============================
@customer_bp.route("/cart")
def cart():
    if not customer_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()

    cur.execute("""
        SELECT c.id, p.title, p.price, c.quantity,
               (p.price * c.quantity) AS total
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.customer_id=%s
    """, (session["user_id"],))

    items = cur.fetchall()

    # ✅ Calculate grand total safely in Python
    grand_total = sum(float(item["total"]) for item in items)

    return render_template(
        "customer/cart.html",
        items=items,
        grand_total=grand_total
    )


# ============================
# UPDATE CART
# ============================
@customer_bp.route("/cart/update", methods=["POST"])
def update_cart():
    if not customer_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()
    cur.execute("""
        UPDATE cart
        SET quantity = %s
        WHERE id = %s AND customer_id = %s
    """, (
        request.form["quantity"],
        request.form["cart_id"],
        session["user_id"]
    ))

    return redirect("/customer/cart")


# ============================
# REMOVE CART ITEM
# ============================
@customer_bp.route("/cart/delete/<int:cart_id>")
def delete_cart(cart_id):
    if not customer_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()
    cur.execute("""
        DELETE FROM cart
        WHERE id = %s AND customer_id = %s
    """, (cart_id, session["user_id"]))

    return redirect("/customer/cart")


@customer_bp.route("/products/<int:product_id>")
def product_detail(product_id):
    if not customer_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()

    cur.execute("""
    SELECT 
        p.*, 
        u.name AS farmer_name,
        u.email AS farmer_email,
        u.created_at AS farmer_joined,
        IFNULL(AVG(r.rating),0) AS avg_rating
    FROM products p
    JOIN users u ON p.farmer_id = u.id
    LEFT JOIN reviews r ON p.id = r.product_id
    WHERE p.id=%s AND p.is_active=1
    GROUP BY p.id
""", (product_id,))


    product = cur.fetchone()

    if not product:
        return redirect("/customer/products")

    # fetch reviews
    cur.execute("""
        SELECT r.rating, r.comment, u.name AS customer_name
        FROM reviews r
        JOIN users u ON r.customer_id = u.id
        WHERE r.product_id=%s
        ORDER BY r.created_at DESC
    """, (product_id,))
    reviews = cur.fetchall()

    return render_template(
        "customer/product_detail.html",
        product=product,
        reviews=reviews
    )


@customer_bp.route("/checkout")
def checkout():
    if not customer_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()

    cur.execute("""
        SELECT 
            c.product_id,
            p.title,
            p.price,
            c.quantity,
            (p.price * c.quantity) AS total,
            p.farmer_id
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.customer_id=%s
    """, (session["user_id"],))

    items = cur.fetchall()

    if not items:
        return redirect("/customer/cart")

    grand_total = sum(float(i["total"]) for i in items)

    return render_template(
        "customer/checkout.html",
        items=items,
        grand_total=grand_total
    )


@customer_bp.route("/checkout/confirm", methods=["POST"])
def confirm_checkout():
    if not customer_only():
        return redirect("/auth/login")

    from collections import defaultdict
    from utils.notifications import create_notification

    payment_method = request.form.get("payment_method", "cod")
    address = request.form.get("address")

    con = get_db()
    cur = con.cursor()

    # Fetch cart items
    cur.execute("""
        SELECT 
            c.product_id,
            p.price,
            c.quantity,
            p.farmer_id
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.customer_id=%s
    """, (session["user_id"],))

    items = cur.fetchall()

    if not items:
        return redirect("/customer/cart")

    # 🔴 STOCK VALIDATION
    for item in items:
        cur.execute("SELECT quantity FROM products WHERE id=%s", (item["product_id"],))
        product = cur.fetchone()

        if int(product["quantity"]) == 0:
            return "This product is currently out of stock."

        elif int(item["quantity"]) > int(product["quantity"]):
            return f"Only {product['quantity']} kg available in stock."


    # 🟢 GROUP ITEMS BY FARMER
    farmer_orders = defaultdict(list)

    for item in items:
        farmer_orders[item["farmer_id"]].append(item)

    # 🔵 CREATE SEPARATE ORDER FOR EACH FARMER
    for farmer_id, farmer_items in farmer_orders.items():

        total_amount = sum(float(i["price"]) * int(i["quantity"]) for i in farmer_items)

        # 1️⃣ CREATE ORDER
        cur.execute("""
            INSERT INTO orders
            (customer_id, farmer_id, total_amount, status, payment_method, address)
            VALUES (%s, %s, %s, 'pending', %s, %s)
        """, (
            session["user_id"],
            farmer_id,
            total_amount,
            payment_method,
            address
        ))

        order_id = cur.lastrowid

        # 2️⃣ REDUCE INVENTORY
        for i in farmer_items:
            cur.execute("""
                UPDATE products
                SET quantity = quantity - %s
                WHERE id=%s
            """, (i["quantity"], i["product_id"]))

        # 3️⃣ CREATE TRANSACTION
        cur.execute("""
            INSERT INTO transactions
            (order_id, farmer_id, amount, payment_method, status)
            VALUES (%s, %s, %s, %s, 'success')
        """, (
            order_id,
            farmer_id,
            total_amount,
            payment_method
        ))

        # 4️⃣ NOTIFY FARMER
        create_notification(
            farmer_id,
            "New Order Received",
            f"You have received a new order #{order_id}",
            "order"
        )

    # 🔔 NOTIFY CUSTOMER
    create_notification(
        session["user_id"],
        "Order Placed",
        "Your order has been placed successfully",
        "order"
    )

    # 🧹 CLEAR CART
    cur.execute("DELETE FROM cart WHERE customer_id=%s", (session["user_id"],))

    return redirect("/customer/orders")

    # ============================
# VIEW ORDERS
# ============================
@customer_bp.route("/orders")
def orders():
    if not customer_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()

    cur.execute("""
        SELECT 
            o.id,
            o.total_amount,
            o.status,
            o.payment_method,
            o.created_at,
            u.name AS farmer_name
        FROM orders o
        JOIN users u ON o.farmer_id = u.id
        WHERE o.customer_id=%s
        ORDER BY o.created_at DESC
    """, (session["user_id"],))

    orders = cur.fetchall()

    return render_template(
        "customer/orders.html",
        orders=orders
    )

