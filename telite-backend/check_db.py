import psycopg

def check_db():
    conn = psycopg.connect('postgresql://postgres:postgres123@localhost:55432/telite_backend')
    cur = conn.cursor()
    
    print("--- INDEXES ---")
    cur.execute("SELECT indexname, indexdef FROM pg_indexes WHERE tablename IN ('courses', 'categories')")
    for row in cur.fetchall():
        print(row)
        
    print("\n--- CONSTRAINTS ---")
    cur.execute("SELECT conname, pg_get_constraintdef(c.oid) FROM pg_constraint c JOIN pg_class t ON c.conrelid = t.oid WHERE t.relname IN ('courses', 'categories') AND c.contype = 'u'")
    for row in cur.fetchall():
        print(row)

if __name__ == '__main__':
    check_db()
