"""Generate a valid JWT access token for the frontend audit.
Uses the backend's security module directly - no database access needed."""
import sys
sys.path.insert(0, '.')

from bike_analyzer.backend.security import create_access_token
import json

# Generate JWT tokens (admin + client)
access_token = create_access_token(
    subject='1',
    is_admin=True,
    tenant_id=1,
    is_client=True,
    athlete_id=1
)

token_data = {
    'access_token': access_token,
    'user': {
        'id': 1,
        'username': 'audit_admin',
        'email': 'admin@test.com',
        'is_admin': True,
        'is_client': True,
        'tenant_id': 1,
        'active_athlete_id': 1
    }
}

with open('D:/BikeMaster/audit_token.json', 'w') as f:
    json.dump(token_data, f, indent=2)

print('Access token (first 60):', access_token[:60])
print('Token saved to audit_token.json')
