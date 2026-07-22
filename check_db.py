import sqlite3
conn = sqlite3.connect('rides.db')
c = conn.cursor()
c.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = [r[0] for r in c.fetchall()]
print('Tables:', tables)
for t in tables:
    if t == 'alembic_version':
        continue
    c.execute(f'SELECT COUNT(*) FROM {t}')
    print(f'{t}: {c.fetchone()[0]}')
conn.close()
