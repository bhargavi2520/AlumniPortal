import sqlite3

def add_col(conn, t, c, d):
    try:
        conn.execute(f"ALTER TABLE {t} ADD COLUMN {c} {d}")
        print(f"Added {c} to {t}")
    except Exception as e:
        print(f"Skipped {c} in {t}: {e}")

def run_migration():
    conn = sqlite3.connect('instance/alumni.db')

    user_cols = [
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

    for c, d in user_cols:
        add_col(conn, 'user', c, d)

    job_cols = [
        ("min_salary", "INTEGER DEFAULT 0"),
        ("max_salary", "INTEGER DEFAULT 0"),
        ("required_experience", "VARCHAR(50) DEFAULT ''"),
        ("required_skills", "VARCHAR(255) DEFAULT ''"),
        ("posted_by_id", "INTEGER DEFAULT 1"),
        ("is_approved", "BOOLEAN DEFAULT True"),
        ("description_embedding", "BLOB"),
        ("ml_status", "VARCHAR(20) DEFAULT 'none'"),
        ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")
    ]

    for c, d in job_cols:
        add_col(conn, 'job', c, d)

    app_cols = [
        ("resume_url", "VARCHAR(255)"),
        ("note", "TEXT DEFAULT ''"),
        ("status", "VARCHAR(50) DEFAULT 'Pending'"),
        ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")
    ]
    
    for c, d in app_cols:
        add_col(conn, 'job_application', c, d)

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == '__main__':
    run_migration()
