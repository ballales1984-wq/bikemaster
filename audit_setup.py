"""Generate a valid JWT token for the frontend audit."""
import sys

sys.path.insert(0, '.')

import json

from bike_analyzer.backend.db.database import get_db_connection, save_athlete
from bike_analyzer.backend.security import create_access_token, hash_password

# Create an admin user directly in SQLite
with get_db_connection() as conn:
    cur = conn.cursor()
    # Check if user exists
    cur.execute("SELECT id, name FROM athletes WHERE name = ?", ("audit_admin",))
    row = cur.fetchone()
    if row:
        print('Athlete already exists:', row)
    else:
        # Create athlete
        athlete_id = save_athlete({
            'name': 'audit_admin',
            'email': 'admin@test.com',
            'experience_level': 'Advanced',
            'password_hash': hash_password('adminpass123'),
            'is_admin': 1
        })
        print('Created athlete ID:', athlete_id)

    # Check users table
    cur.execute("SELECT id, username, is_admin FROM users WHERE username = ?", ("audit_admin",))
    urow = cur.fetchone()
    print('Users table row:', urow)
    if not urow:
        cur.execute(
            "INSERT INTO users (username, email, password_hash, is_admin, is_client, is_active, created_at, updated_at) VALUES (?, ?, ?, 1, 1, 1, ?, ?)",
            ("audit_admin", "admin@test.com", hash_password("adminpass123"), "2024-01-01", "2024-01-01")
        )
        conn.commit()
        cur.execute("SELECT id, username, is_admin FROM users WHERE username = ?", ("audit_admin",))
        print('Created user:', cur.fetchone())

# Generate JWT token with admin claims
token = create_access_token(
    subject='1',
    is_admin=True,
    tenant_id=1,
    is_client=True,
    athlete_id=1
)
print('Token (first 50):', token[:50])

# Build the user object that matches what the frontend expects
user_obj = {
    'id': 1,
    'username': 'audit_admin',
    'email': 'admin@test.com',
    'is_admin': True,
    'is_client': True,
    'tenant_id': 1,
    'active_athlete_id': 1
}

# Save token and user for the frontend audit
with open('D:/BikeMaster/audit_token.txt', 'w') as f:
    f.write(token)

with open('D:/BikeMaster/audit_user.json', 'w') as f:
    json.dump(user_obj, f)

print('Token and user data saved.')
