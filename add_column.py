import sqlite3

try:
    conn = sqlite3.connect('instance/alumni.db')
    c = conn.cursor()
    c.execute("ALTER TABLE job_application ADD COLUMN resume_url VARCHAR(255)")
    conn.commit()
    print("Successfully added resume_url column to job_application table.")
except Exception as e:
    print(f"Error (column might already exist): {e}")
finally:
    if 'conn' in locals():
        conn.close()
