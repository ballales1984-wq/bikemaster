import time, json, hashlib
from jose import jwt
from bike_analyzer.backend.security import SECRET_KEY, ALGORITHM, JWT_ISSUER, JWT_AUDIENCE

print(f'JWT_ISSUER: {repr(JWT_ISSUER)}')
print(f'JWT_AUDIENCE: {repr(JWT_AUDIENCE)}')
print(f'ALGORITHM: {ALGORITHM}')
print(f'SECRET_KEY: {SECRET_KEY[:15]}...')

now = int(time.time())
jti = hashlib.sha256(f"1:{time.time()}:{SECRET_KEY}".encode()).hexdigest()[:32]

payload = {
    "sub": "1",
    "is_admin": True,
    "is_client": True,
    "iat": now,
    "exp": now + 3600,
    "iss": JWT_ISSUER,
    "aud": JWT_AUDIENCE,
    "jti": jti,
    "tenant_id": 1,
    "athlete_id": 1,
}

print(f'\nNow: {now}')
print(f'Payload: {json.dumps(payload)}')

# Use python-jose jwt.encode (same as backend)
token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
print(f'\nToken: {token}')

# Verify
from bike_analyzer.backend.security import _try_decode
result = _try_decode(token, SECRET_KEY)
if result:
    print('\nVerification: PASSED')
    print(f'Decoded: iss={result.get("iss")}, exp={result.get("exp")}')
else:
    print('\nVerification: FAILED')
