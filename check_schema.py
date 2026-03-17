import sqlite3
import json
conn = sqlite3.connect('instance/alumni.db')
cursor = conn.cursor()
tables = ['user', 'job', 'job_application', 'connection', 'announcement', 'message', 'audit_log']
schema = {}
for table in tables:
    try:
        cursor.execute(f"PRAGMA table_info({table})")
        schema[table] = [row[1] for row in cursor.fetchall()]
    except Exception as e:
        schema[table] = str(e)
with open('schema_output.json', 'w') as f:
    json.dump(schema, f, indent=2)
