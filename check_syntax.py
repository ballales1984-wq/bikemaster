with open('bike_analyzer/backend/db/database.py', 'rb') as f:
    content = f.read()
    print('First 100 bytes hex:', content[:100].hex())
    print('First 4 bytes:', content[:4])
    print('First 4 decoded:', content[:4].decode('utf-8', errors='replace'))
    
    lines = content.split(b'\n')
    # Check first few lines
    for i in range(0, 10):
        line = lines[i]
        print(f'Line {i+1}: {line[:60].decode("utf-8", errors="replace")!r}')
