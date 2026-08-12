"""Script to add @pg_dispatch decorators to all public functions in database.py."""

from __future__ import annotations

import re

with open("bike_analyzer/backend/db/database.py", "r", encoding="utf-8") as f:
    content = f.read()

lines = content.split('\n')

# Functions to skip (core infrastructure, not domain data)
SKIP_FUNCS = {
    "get_db_connection",
    "init_db",
    "recalculate_training_stress_for_athlete",
    "acquire_oauth_sqlite_lock",
    "release_oauth_sqlite_lock",
    "create_indices",
    "backup_database",
    "get_backup_dir",
    "rotate_backups",
    "scheduled_backup",
}

new_lines = []
added = 0
skipped = 0

i = 0
while i < len(lines):
    line = lines[i]
    
    # Check if this is a public function definition
    if line.startswith("def ") and not line.startswith("def _"):
        func_name = line.split("(")[0].replace("def ", "")
        
        # Check if already has @pg_dispatch
        j = i - 1
        while j >= 0 and lines[j].strip() == "":
            j -= 1
        
        if j >= 0 and lines[j].strip().startswith("@pg_dispatch"):
            # Already decorated
            new_lines.append(line)
            i += 1
            continue
        
        # Check if should skip
        if func_name in SKIP_FUNCS:
            skipped += 1
            new_lines.append(line)
            i += 1
            continue
        
        # Add @pg_dispatch decorator
        module = "bike_analyzer.backend.db.postgres_stubs"
        new_lines.append(f'@pg_dispatch("{module}")')
        new_lines.append(line)
        added += 1
        i += 1
        continue
    
    new_lines.append(line)
    i += 1

with open("bike_analyzer/backend/db/database.py", "w", encoding="utf-8") as f:
    f.write('\n'.join(new_lines))

print(f"Added @pg_dispatch to {added} functions")
print(f"Skipped {skipped} core infrastructure functions")
print("Done!")
