import json, base64
from bike_analyzer.backend.security import _try_decode, JWT_ISSUER, JWT_AUDIENCE, SECRET_KEY
import time

token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiaXNfYWRtaW4iOnRydWUsImlzX2NsaWVudCI6dHJ1ZSwiaWF0IjoxNzQ1NzQ3ZTU5LCJleHAiOjE3NDU3NDU1NTksImlzcyI6ImJpa2VtZXN0ZXIiLCJhdWQiOiJiaWtlbWFzdGVyIiwianRpIjoiODI0ZmFjYWFhODYyNDM1M2MzMjhkYzYxYmUyZTc3MTIiLCJ0ZW5hbnRfaWQiOjEsImF0aGxldGVfaWQiOjF9.Ps_b3E5EZdNcfq39AaIZFyd-_SqNHERXfKudvH52IEc'

# Decode payload properly
parts = token.split('.')
payload_b64 = parts[1]
padded = payload_b64 + '=' * (4 - len(payload_b64) % 4)
decoded_bytes = base64.urlsafe_b64decode(padded)
decoded_str = decoded_bytes.decode('utf-8')
print('Raw payload JSON:', decoded_str)
payload = json.loads(decoded_str)
print()
print('iss:', repr(payload.get('iss')))
print('aud:', repr(payload.get('aud')))
print('iat:', payload.get('iat'))
print('exp:', payload.get('exp'))
print('iss matches:', payload.get('iss') == JWT_ISSUER)
print('aud matches:', payload.get('aud') == JWT_AUDIENCE)
print('exp > now:', (payload.get('exp', 0) or 0) > time.time())
print('now:', time.time())
print()

# Test backend decode
result = _try_decode(token, SECRET_KEY)
print('_try_decode result:', result if result else 'None (FAILED)')
