from flask import Blueprint, render_template, session, redirect
from db import get_db

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
    template_folder="templates/admin"
)

def admin_only():
    return session.get("role") == "admin"


@admin_bp.route("/dashboard")
def dashboard():
    if not admin_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) AS total_users FROM users")
    total_users = cur.fetchone()["total_users"]

    cur.execute("SELECT COUNT(*) AS total_orders FROM orders")
    total_orders = cur.fetchone()["total_orders"]

    cur.execute("""
        SELECT COUNT(*) AS pending_farmers
        FROM users
        WHERE role='farmer' AND status='pending'
    """)
    pending_farmers = cur.fetchone()["pending_farmers"]

    cur.execute("SELECT IFNULL(SUM(total_amount),0) AS revenue FROM orders WHERE status='delivered'")
    revenue = cur.fetchone()["revenue"]

    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        total_orders=total_orders,
        pending_farmers=pending_farmers,
        revenue=revenue
    )

@admin_bp.route("/farmers")
def farmers():
    if not admin_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()

    cur.execute("""
        SELECT id, name, email, status, created_at
        FROM users
        WHERE role='farmer'
        ORDER BY created_at DESC
    """)
    farmers = cur.fetchall()

    return render_template("admin/farmers.html", farmers=farmers)

@admin_bp.route("/farmers/approve/<int:user_id>")
def approve_farmer(user_id):
    if not admin_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()
    cur.execute("""
        UPDATE users
        SET status='active'
        WHERE id=%s AND role='farmer'
    """, (user_id,))
    return redirect("/admin/farmers")


@admin_bp.route("/farmers/ban/<int:user_id>")
def ban_farmer(user_id):
    if not admin_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()
    cur.execute("""
        UPDATE users
        SET status='banned'
        WHERE id=%s AND role='farmer'
    """, (user_id,))
    return redirect("/admin/farmers")


@admin_bp.route("/customers")
def customers():
    if not admin_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()

    cur.execute("""
        SELECT id, name, email, status, created_at
        FROM users
        WHERE role='customer'
        ORDER BY created_at DESC
    """)
    customers = cur.fetchall()

    return render_template("admin/customers.html", customers=customers)


@admin_bp.route("/customers/ban/<int:user_id>")
def ban_customer(user_id):
    if not admin_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()
    cur.execute("""
        UPDATE users
        SET status='banned'
        WHERE id=%s AND role='customer'
    """, (user_id,))
    return redirect("/admin/customers")


@admin_bp.route("/orders")
def orders():
    if not admin_only():
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
            c.name AS customer_name,
            f.name AS farmer_name
        FROM orders o
        JOIN users c ON o.customer_id = c.id
        JOIN users f ON o.farmer_id = f.id
        ORDER BY o.created_at DESC
    """)
    orders = cur.fetchall()

    return render_template("admin/orders.html", orders=orders)


@admin_bp.route("/transactions")
def transactions():
    if not admin_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()

    cur.execute("""
        SELECT
            t.id,
            t.amount,
            t.payment_method,
            t.status,
            t.created_at,
            o.id AS order_id,
            u.name AS farmer_name
        FROM transactions t
        JOIN orders o ON t.order_id = o.id
        JOIN users u ON t.farmer_id = u.id
        ORDER BY t.created_at DESC
    """)
    transactions = cur.fetchall()

    return render_template("admin/transactions.html", transactions=transactions)


@admin_bp.route("/complaints")
def complaints():
    if not admin_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()
    cur.execute("""
        SELECT c.*, u.name, u.role
        FROM complaints c
        JOIN users u ON c.user_id = u.id
        ORDER BY c.created_at DESC
    """)
    complaints = cur.fetchall()

    return render_template("admin/complaints.html", complaints=complaints)


@admin_bp.route("/complaints/close/<int:cid>")
def close_complaint(cid):
    if not admin_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()
    cur.execute("""
        UPDATE complaints SET status='closed' WHERE id=%s
    """, (cid,))
    return redirect("/admin/complaints")



@admin_bp.route("/customers/approve/<int:user_id>")
def unban_customer(user_id):
    if not admin_only():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()
    cur.execute("""
        UPDATE users
        SET status='active'
        WHERE id=%s AND role='customer'
    """, (user_id,))
    return redirect("/admin/customers")
