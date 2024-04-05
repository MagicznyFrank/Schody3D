import sqlite3

DATABASE_NAME = 'main.db'

def create_connection():
    return sqlite3.connect(DATABASE_NAME)

def execute_query(query, args=None):
    conn = create_connection()
    cursor = conn.cursor()
    if args:
        cursor.execute(query, args)
    else:
        cursor.execute(query)
    conn.commit()
    conn.close()

def fetch_data(query, args=None):
    conn = create_connection()
    cursor = conn.cursor()
    if args:
        cursor.execute(query, args)
    else:
        cursor.execute(query)
    data = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]
    conn.close()
    return data
