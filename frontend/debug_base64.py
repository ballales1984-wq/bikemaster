import base64, json

# Direct test: encode and decode "bikemaster"
test_str = '{"iss":"bikemaster"}'
encoded = base64.urlsafe_b64encode(test_str.encode()).rstrip(b'=').decode('ascii')
print(f'JSON: {test_str}')
print(f'Base64: {encoded}')
decoded = base64.urlsafe_b64decode(encoded + '=' * (4 - len(encoded) % 4))
print(f'Decoded: {decoded.decode()}')
print()

# Now try with the actual payload dict
from bike_analyzer.backend.security import JWT_ISSUER, JWT_AUDIENCE, SECRET_KEY
import time, hashlib

now = int(time.time())
jti = hashlib.sha256(f"1:{time.time()}:{SECRET_KEY}".encode()).hexdigest()[:32]

payload = {
    "sub": "1",
    "is_admin": True,
    "iss": JWT_ISSUER,  # Should be 'bikemaster'
    "aud": JWT_AUDIENCE,
}

print(f'JWT_ISSUER type: {type(JWT_ISSUER)}')
print(f'JWT_ISSUER value: {repr(JWT_ISSUER)}')
print(f'JWT_ISSUER bytes: {JWT_ISSUER.encode()}')
print(f'JWT_ISSUER hex: {JWT_ISSUER.encode().hex()}')

json_str = json.dumps(payload, separators=(',', ':'))
print(f'JSON string: {json_str}')
print(f'JSON contains bikemaster: {"bikemaster" in json_str}')
print(f'JSON contains bikemester: {"bikemester" in json_str}')

b64 = base64.urlsafe_b64encode(json_str.encode()).rstrip(b'=').decode('ascii')
print(f'Base64: {b64}')

# Decode back
decoded = base64.urlsafe_b64decode(b64 + '=' * (4 - len(b64) % 4))
decoded_str = decoded.decode('utf-8')
print(f'Decoded back: {decoded_str}')
print(f'Decoded contains bikemaster: {"bikemaster" in decoded_str}')
print(f'Decoded contains bikemester: {"bikemester" in decoded_str}')
