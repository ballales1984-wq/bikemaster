with open('bike_analyzer/backend/db/database.py', 'r') as f:
    lines = f.readlines()

# Aggiungi migrazione email dopo password_hash
for i, line in enumerate(lines):
    if 'ALTER TABLE athletes ADD COLUMN password_hash TEXT' in line:
        lines.insert(i+1, '        if "email" not in columns:\n')
        lines.insert(i+2, '            conn.execute("ALTER TABLE athletes ADD COLUMN email TEXT")\n')
        print(f'Added email migration after line {i}')
        break

with open('bike_analyzer/backend/db/database.py', 'w') as f:
    f.writelines(lines)
print('Done')