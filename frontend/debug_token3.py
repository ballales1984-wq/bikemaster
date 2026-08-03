import base64, json

token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiaXNfYWRtaW4iOnRydWUsImlzX2NsaWVudCI6dHJ1ZSwiaWF0IjoxNzQ1NzUyNTE2LCJleHAiOjE3ODU3NTYxMTYsImlzcyI6ImJpa2VtZXN0ZXIiLCJhdWQiOiJiaWtlbWFzdGVyIiwianRpIjoiZDc2YTJhNDcyOTZiY2E4ODBjY2I1NGFkMGE5NDBhNjAiLCJ0ZW5hbnRfaWQiOjEsImF0aGxldGVfaWQiOjF9.1rrAO5LNDWHyXfQe50NNkbVenQIh3rEUCLlF7nbC9dc'

parts = token.split('.')
payload_b64 = parts[1]
# Add padding
padded = payload_b64 + '=' * (4 - len(payload_b64) % 4)
decoded = base64.urlsafe_b64decode(padded)
print('Raw decoded bytes:', repr(decoded))
print()
print('Decoded JSON:', json.dumps(json.loads(decoded), indent=2))

# Also decode header
header_b64 = parts[0]
padded_h = header_b64 + '=' * (4 - len(header_b64) % 4)
decoded_h = base64.urlsafe_b64decode(padded_h)
print('Header:', json.dumps(json.loads(decoded_h), indent=2))
