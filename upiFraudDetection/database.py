import sqlite3

DB_PATH = "upi_fraud.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_table():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fraud_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            upi_num TEXT,
            merchant TEXT,
            amount REAL,
            status TEXT,
            dob TEXT,
            trans_datetime TEXT,
            result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()

create_table()
