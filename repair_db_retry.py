import sqlite3
import os

def repair_db():
    db_path = 'instance/alumni.db'
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    def get_columns(table_name):
        try:
            cursor.execute(f"PRAGMA table_info({table_name})")
            return [row[1] for row in cursor.fetchall()]
        except:
            return []

    def add_column(table_name, column_name, column_type):
        existing_columns = get_columns(table_name)
        if column_name not in existing_columns:
            try:
                # SQLite ALTER TABLE cannot add columns with UNIQUE or NOT NULL without default
                # Removing UNIQUE for now to ensure the column is added and app stops crashing
                sql_type = column_type.replace("UNIQUE", "")
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {sql_type}")
                print(f"Added column '{column_name}' to table '{table_name}'.")
            except Exception as e:
                print(f"Error adding column '{column_name}' to '{table_name}': {e}")
        else:
            print(f"Column '{column_name}' already exists in table '{table_name}'.")

    # Column definitions from app.py models
    user_columns = [
        ("roll_number", "VARCHAR(100)"), # UNIQUE removed for compatibility
        ("joined_year", "VARCHAR(10) DEFAULT ''"),
        ("graduation_duration", "VARCHAR(20) DEFAULT ''"),
        ("resume_filename", "VARCHAR(255) DEFAULT ''"),
        ("resume_embedding", "PickleType"), # Using general type for BLOB/Pickle
        ("resume_ml_status", "VARCHAR(20) DEFAULT 'none'"),
        ("is_verified", "BOOLEAN DEFAULT False"),
        ("verification_status", "VARCHAR(20) DEFAULT 'pending'"),
        ("verified_by_id", "INTEGER"),
        ("verified_at", "DATETIME"),
        ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
        ("failed_login_attempts", "INTEGER DEFAULT 0"),
        ("account_locked_until", "DATETIME")
    ]

    job_columns = [
        ("min_salary", "INTEGER DEFAULT 0"),
        ("max_salary", "INTEGER DEFAULT 0"),
        ("required_experience", "VARCHAR(50) DEFAULT ''"),
        ("required_skills", "VARCHAR(255) DEFAULT ''"),
        ("posted_by_id", "INTEGER DEFAULT 1"),
        ("is_approved", "BOOLEAN DEFAULT True"),
        ("description_embedding", "PickleType"),
        ("ml_status", "VARCHAR(20) DEFAULT 'none'"),
        ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")
    ]

    app_columns = [
        ("resume_url", "VARCHAR(255)"),
        ("note", "TEXT DEFAULT ''"),
        ("status", "VARCHAR(50) DEFAULT 'Pending'"),
        ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")
    ]

    print("Starting database repair (Retry)...")
    for col_name, col_type in user_columns:
        add_column('user', col_name, col_type)
    
    for col_name, col_type in job_columns:
        add_column('job', col_name, col_type)

    for col_name, col_type in app_columns:
        add_column('job_application', col_name, col_type)

    conn.commit()
    conn.close()
    print("Database repair (Retry) complete.")

if __name__ == "__main__":
    repair_db()
