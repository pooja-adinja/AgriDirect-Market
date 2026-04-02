import pymysql

def get_db():
    return pymysql.connect(
        host="localhost",
        port=3306,
        user="root",
        password="",
        database="agri_direct_market",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )
