from db import get_db

def create_notification(user_id, title, message, ntype="system"):
    con = get_db()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO notifications (user_id, title, message, type)
        VALUES (%s, %s, %s, %s)
    """, (user_id, title, message, ntype))
