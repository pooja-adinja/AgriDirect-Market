from flask import Flask, redirect, render_template,session
from auth import auth_bp
from admin import admin_bp
from farmer import farmer_bp
from customer import customer_bp
from complaints import complaint_bp
from notifications import notification_bp
from db import get_db

app = Flask(__name__)
app.secret_key = "agridirect-secret"

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(farmer_bp)
app.register_blueprint(customer_bp)
app.register_blueprint(complaint_bp)
app.register_blueprint(notification_bp)



# ----------------------------
# ROOT REDIRECT
# ----------------------------
@app.route("/")
def home():
    return render_template("landing.html")
    if "user_id" not in session:
        return redirect("/auth/login")

    role = session.get("role")

    if role == "admin":
        return redirect("/admin/dashboard")
    elif role == "farmer":
        return redirect("/farmer/dashboard")
    elif role == "customer":
        return redirect("/customer/dashboard")

@app.context_processor
def inject_notifications():
    if "user_id" not in session:
        return {}

    con = get_db()
    cur = con.cursor()
    cur.execute("""
        SELECT COUNT(*) AS cnt
        FROM notifications
        WHERE user_id=%s AND is_read=0
    """, (session["user_id"],))

    return {"unread_count": cur.fetchone()["cnt"]}



if __name__ == "__main__":
    app.run(debug=True)
