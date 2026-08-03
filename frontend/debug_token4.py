import time, json, hashlib, hmac, base64
from bike_analyzer.backend.security import SECRET_KEY, ALGORITHM, JWT_ISSUER, JWT_AUDIENCE

print(f'JWT_ISSUER: {repr(JWT_ISSUER)}')
print(f'JWT_AUDIENCE: {repr(JWT_AUDIENCE)}')
print(f'SECRET_KEY: {SECRET_KEY[:10]}...')

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

# Encode header
header = {"alg": "HS256", "typ": "JWT"}
def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')

header_json = json.dumps(header, separators=(',', ':'))
payload_json = json.dumps(payload, separators=(',', ':'))
print(f'\nHeader JSON: {header_json}')
print(f'Payload JSON: {payload_json}')

header_b64 = b64url(header_json.encode())
payload_b64 = b64url(payload_json.encode())
print(f'\nHeader b64: {header_b64}')
print(f'Payload b64: {payload_b64}')

signing_input = f"{header_b64}.{payload_b64}".encode()
signature = hmac.new(SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
signature_b64 = b64url(signature)

token = f"{header_b64}.{payload_b64}.{signature_b64}"
print(f'\nToken: {token}')

# Verify by decoding back
parts = token.split('.')
decoded_payload = b64url(parts[1])  # won't work, need padding
padded = parts[1] + '=' * (4 - len(parts[1]) % 4)
decoded = base64.urlsafe_b64decode(padded)
print(f'\nDecoded payload: {decoded.decode()}')
print(f'Decoded payload JSON: {json.loads(decoded)}')

# Test with backend
from bike_analyzer.backend.security import _try_decode
result = _try_decode(token, SECRET_KEY)
print(f'\n_try_decode: {result}')
if result:
    print('TOKEN IS VALID FOR BACKEND')
else:
    print('TOKEN IS INVALID FOR BACKEND')
