from flask import Blueprint, render_template, request, redirect, session
from db import get_db
import hashlib
import re

auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth",
    template_folder="templates/auth"
)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def redirect_if_logged_in():
    if "user_id" in session:
        role = session.get("role")
        if role == "admin":
            return redirect("/admin/dashboard")
        elif role == "farmer":
            return redirect("/farmer/dashboard")
        elif role == "customer":
            return redirect("/customer/dashboard")
    return None


# ----------------------------
# LOGIN
# ----------------------------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # ✅ already logged in → dashboard
    redirect_resp = redirect_if_logged_in()
    if redirect_resp:
        return redirect_resp

    error = None

    if request.method == "POST":
        email = request.form["email"]
        password = hash_password(request.form["password"])

        con = get_db()
        cur = con.cursor()
        cur.execute("""
            SELECT * FROM users
            WHERE email=%s AND password_hash=%s AND status='active'
        """, (email, password))
        user = cur.fetchone()

        if user:
            session["user_id"] = user["id"]
            session["role"] = user["role"]

            return redirect_if_logged_in()
        else:
            error = "Invalid credentials or inactive account"

    return render_template("login.html", error=error)


# ----------------------------
# REGISTER
# ----------------------------
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    # ✅ already logged in → dashboard
    redirect_resp = redirect_if_logged_in()
    if redirect_resp:
        return redirect_resp

    error = None

    if request.method == "POST":
        name = request.form["name"].strip()
        if not re.fullmatch(r"[A-Za-z ]+", name):
            error = "Name should contain only alphabets and spaces"
            return render_template("register.html", error=error)
        
        email = request.form["email"].strip()

# Reject if email contains uppercase letters
        if email != email.lower():
            error = "Email must contain only lowercase letters"
            return render_template("register.html", error=error)

# Strict lowercase email pattern
        email_pattern = r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$"

        if not re.fullmatch(email_pattern, email):
            error = "Invalid email format"
            return render_template("register.html", error=error)

        role = request.form["role"]  # customer / farmer
        password = hash_password(request.form["password"])

        con = get_db()
        cur = con.cursor()

        try:
            cur.execute("""
                INSERT INTO users (name, email, password_hash, role, status)
                VALUES (%s, %s, %s, %s, 'active')
            """, (name, email, password, role))

            return redirect("/auth/login")
        except:
            error = "Email already exists"

    return render_template("register.html", error=error)


# ----------------------------
# LOGOUT
# ----------------------------
@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")
