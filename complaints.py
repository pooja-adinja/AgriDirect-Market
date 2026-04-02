from flask import Blueprint, render_template, request, redirect, session
from db import get_db

complaint_bp = Blueprint(
    "complaint",
    __name__,
    url_prefix="/complaints",
    template_folder="templates/complaints"
)

def logged_in():
    return session.get("user_id") is not None


@complaint_bp.route("/", methods=["GET", "POST"])
def submit_complaint():
    if not logged_in():
        return redirect("/auth/login")

    if request.method == "POST":
        subject = request.form["subject"]
        message = request.form["message"]

        con = get_db()
        cur = con.cursor()
        cur.execute("""
            INSERT INTO complaints (user_id, subject, message)
            VALUES (%s, %s, %s)
        """, (
            session["user_id"],
            subject,
            message
        ))

        return redirect("/complaints?success=1")

    return render_template("complaints/complaints.html")
