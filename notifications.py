from flask import Blueprint, render_template, session, redirect
from db import get_db

notification_bp = Blueprint(
    "notifications",
    __name__,
    url_prefix="/notifications"
)

def logged_in():
    return "user_id" in session


@notification_bp.route("/")
def list_notifications():
    if not logged_in():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()

    cur.execute("""
        SELECT *
        FROM notifications
        WHERE user_id=%s
        ORDER BY created_at DESC
    """, (session["user_id"],))

    notifications = cur.fetchall()

    return render_template(
        "notifications/list.html",
        notifications=notifications
    )


@notification_bp.route("/read/<int:nid>")
def mark_read(nid):
    if not logged_in():
        return redirect("/auth/login")

    con = get_db()
    cur = con.cursor()
    cur.execute("""
        UPDATE notifications
        SET is_read=1
        WHERE id=%s AND user_id=%s
    """, (nid, session["user_id"]))

    return redirect("/notifications")
