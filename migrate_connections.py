import sqlite3

try:
    conn = sqlite3.connect('instance/alumni.db')
    c = conn.cursor()
    c.execute("""
    CREATE TABLE connection (
        id INTEGER NOT NULL PRIMARY KEY, 
        sender_id INTEGER NOT NULL, 
        receiver_id INTEGER NOT NULL, 
        status VARCHAR(20), 
        created_at DATETIME, 
        FOREIGN KEY(sender_id) REFERENCES user (id), 
        FOREIGN KEY(receiver_id) REFERENCES user (id), 
        CONSTRAINT uq_connection UNIQUE (sender_id, receiver_id)
    );
    """)
    print("Added connection table")
except Exception as e:
    print(f"Error for connection (might exist): {e}")

if 'conn' in locals():
    conn.commit()
    conn.close()
