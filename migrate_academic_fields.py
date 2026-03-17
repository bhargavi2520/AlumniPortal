import sqlite3

try:
    conn = sqlite3.connect('instance/alumni.db')
    c = conn.cursor()
    c.execute("ALTER TABLE user ADD COLUMN roll_number VARCHAR(100) UNIQUE;")
    print("Added roll_number")
except Exception as e:
    print(f"Error for roll_number (might exist): {e}")

try:
    c.execute("ALTER TABLE user ADD COLUMN joined_year VARCHAR(10);")
    print("Added joined_year")
except Exception as e:
    print(f"Error for joined_year (might exist): {e}")

try:
    c.execute("ALTER TABLE user ADD COLUMN graduation_duration VARCHAR(20);")
    print("Added graduation_duration")
except Exception as e:
    print(f"Error for graduation_duration (might exist): {e}")

if 'conn' in locals():
    conn.commit()
    conn.close()
