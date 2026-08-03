import asyncio
from bike_analyzer.backend.security import decode_token, _try_decode, SECRET_KEY, JWT_ISSUER, JWT_AUDIENCE

token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiaXNfYWRtaW4iOnRydWUsImlzX2NsaWVudCI6dHJ1ZSwiaWF0IjoxNzQ1NzUyNTE2LCJleHAiOjE3ODU3NTYxMTYsImlzcyI6ImJpa2VtZXN0ZXIiLCJhdWQiOiJiaWtlbWFzdGVyIiwianRpIjoiZDc2YTJhNDcyOTZiY2E4ODBjY2I1NGFkMGE5NDBhNjAiLCJ0ZW5hbnRfaWQiOjEsImF0aGxldGVfaWQiOjF9.1rrAO5LNDWHyXfQe50NNkbVenQIh3rEUCLlF7nbC9dc'

print(f'SECRET_KEY: {SECRET_KEY}')
print(f'JWT_ISSUER: {repr(JWT_ISSUER)}')
print(f'JWT_AUDIENCE: {repr(JWT_AUDIENCE)}')

# Test _try_decode directly
result = _try_decode(token, SECRET_KEY)
print(f'\n_try_decode result: {result}')

# Test full decode_token
async def test_decode():
    try:
        payload = await decode_token(token)
        print(f'decode_token result: {payload}')
    except Exception as e:
        print(f'decode_token error: {type(e).__name__}: {e}')

asyncio.run(test_decode())
