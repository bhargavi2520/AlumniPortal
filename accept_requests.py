import sqlite3

def find_and_accept():
    conn = sqlite3.connect('instance/alumni.db')
    cursor = conn.cursor()

    # Find Bhargavi
    cursor.execute("SELECT id, full_name, role FROM user WHERE full_name LIKE '%bhargavi%'")
    users = cursor.fetchall()
    
    if not users:
        print("No user found matching 'bhargavi'")
        return

    for user_id, name, role in users:
        print(f"Found user: {name} (ID: {user_id}, Role: {role})")
        
        # Find pending requests FROM Bhargavi
        cursor.execute("SELECT id, receiver_id FROM connection WHERE sender_id = ? AND status = 'pending'", (user_id,))
        requests = cursor.fetchall()
        
        if not requests:
            print(f"No pending requests found from {name}")
            continue

        print(f"Found {len(requests)} pending requests from {name}")
        
        for req_id, receiver_id in requests:
            # Check if receiver is an alumni
            cursor.execute("SELECT role FROM user WHERE id = ?", (receiver_id,))
            receiver_role = cursor.fetchone()
            
            if receiver_role and receiver_role[0] == 'alumni':
                cursor.execute("UPDATE connection SET status = 'accepted' WHERE id = ?", (req_id,))
                print(f"Accepted request {req_id} to Alumni (ID: {receiver_id})")
            else:
                print(f"Skipping request {req_id} as receiver is not an alumni (Role: {receiver_role[0] if receiver_role else 'unknown'})")

    conn.commit()
    conn.close()
    print("Process complete.")

if __name__ == "__main__":
    find_and_accept()
