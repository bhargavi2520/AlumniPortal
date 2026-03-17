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
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in cursor.fetchall()]

    def add_column(table_name, column_name, column_type):
        existing_columns = get_columns(table_name)
        if column_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
                print(f"Added column '{column_name}' to table '{table_name}'.")
            except Exception as e:
                print(f"Error adding column '{column_name}' to '{table_name}': {e}")
        else:
            print(f"Column '{column_name}' already exists in table '{table_name}'.")

    # missing columns for 'user' table
    user_columns = [
        ("roll_number", "VARCHAR(100) UNIQUE"),
        ("joined_year", "VARCHAR(10) DEFAULT ''"),
        ("graduation_duration", "VARCHAR(20) DEFAULT ''"),
        ("resume_filename", "VARCHAR(255) DEFAULT ''"),
        ("resume_embedding", "BLOB"),
        ("resume_ml_status", "VARCHAR(20) DEFAULT 'none'"),
        ("is_verified", "BOOLEAN DEFAULT False"),
        ("verification_status", "VARCHAR(20) DEFAULT 'pending'"),
        ("verified_by_id", "INTEGER"),
        ("verified_at", "DATETIME"),
        ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
        ("failed_login_attempts", "INTEGER DEFAULT 0"),
        ("account_locked_until", "DATETIME")
    ]

    # missing columns for 'job' table
    job_columns = [
        ("min_salary", "INTEGER DEFAULT 0"),
        ("max_salary", "INTEGER DEFAULT 0"),
        ("required_experience", "VARCHAR(50) DEFAULT ''"),
        ("required_skills", "VARCHAR(255) DEFAULT ''"),
        ("posted_by_id", "INTEGER DEFAULT 1"), # Assuming a default admin/system user ID
        ("is_approved", "BOOLEAN DEFAULT True"),
        ("description_embedding", "BLOB"),
        ("ml_status", "VARCHAR(20) DEFAULT 'none'"),
        ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")
    ]

    # missing columns for 'job_application' table
    app_columns = [
        ("resume_url", "VARCHAR(255)"),
        ("note", "TEXT DEFAULT ''"),
        ("status", "VARCHAR(50) DEFAULT 'Pending'"),
        ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")
    ]

    print("Starting database repair...")
    for col_name, col_type in user_columns:
        add_column('user', col_name, col_type)
    
    for col_name, col_type in job_columns:
        add_column('job', col_name, col_type)

    for col_name, col_type in app_columns:
        add_column('job_application', col_name, col_type)

    conn.commit()
    conn.close()
    print("Database repair complete.")

if __name__ == "__main__":
    repair_db()
