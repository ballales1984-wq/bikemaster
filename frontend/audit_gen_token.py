"""
Generate a valid JWT token for BikeMaster audit testing.
Bypasses create_access_token which has a datetime serialization bug.
"""
import time
import json
import hashlib
import hmac
from bike_analyzer.backend.security import SECRET_KEY, ALGORITHM, JWT_ISSUER, JWT_AUDIENCE

def base64url_encode(data):
    """Base64url encode without padding."""
    import base64
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')

def generate_token(subject='1', is_admin=True, is_client=True, tenant_id=1, athlete_id=1):
    """Generate a valid JWT token with correct claims."""
    now = int(time.time())
    jti = hashlib.sha256(f"{subject}:{time.time()}:{SECRET_KEY}".encode()).hexdigest()[:32]

    payload = {
        "sub": str(subject),
        "is_admin": is_admin,
        "is_client": is_client,
        "iat": now,
        "exp": now + 3600,  # 1 hour expiry
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "jti": jti,
        "tenant_id": tenant_id,
        "athlete_id": athlete_id,
    }

    header = {"alg": ALGORITHM, "typ": "JWT"}
    header_b64 = base64url_encode(json.dumps(header, separators=(',', ':')).encode())
    payload_b64 = base64url_encode(json.dumps(payload, separators=(',', ':')).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
    signature_b64 = base64url_encode(signature)

    token = f"{header_b64}.{payload_b64}.{signature_b64}"
    return token, payload

token, payload = generate_token()
print("Token:", token)
print("\nPayload:", json.dumps(payload, indent=2))

# Verify
from bike_analyzer.backend.security import _try_decode, decode_token
import asyncio

result = _try_decode(token, SECRET_KEY)
if result:
    print("\nVerification: PASSED - token decodes correctly")
    print("Decoded:", result)
else:
    print("\nVerification: FAILED")
