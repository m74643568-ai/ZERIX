import sqlite3

def create_tables():
    conn = sqlite3.connect("zerix.db")
    c = conn.cursor()

    # جدول المستخدمين
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            email TEXT
        )
    """)

    conn.commit()
    conn.close()

# إنشاء الجداول لأول مرة
create_tables()
