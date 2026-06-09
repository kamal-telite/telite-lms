import sqlite3

def drop_tables():
    conn = sqlite3.connect('telite.db')
    cursor = conn.cursor()
    cursor.execute('DROP TABLE IF EXISTS builder_activity_log')
    cursor.execute('DROP TABLE IF EXISTS course_edit_locks')
    conn.commit()
    conn.close()
    print("Tables dropped successfully.")

if __name__ == "__main__":
    drop_tables()
