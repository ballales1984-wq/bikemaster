"""Fix script to add email column to save_athlete INSERT statement."""

with open("bike_analyzer/backend/db/database.py", "r") as f:
    lines = f.readlines()

# Aggiungi email dopo name nel primo INSERT di save_athlete
for i, line in enumerate(lines):
    if "INSERT INTO athletes (name, age, weight_kg, height_cm, fat_percentage," in line:
        lines[i] = '                """INSERT INTO athletes (name, email, age, weight_kg, height_cm, fat_percentage,\n'
        lines[i - 1] = '                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""\n'
        # Aggiungi email nei valori dopo name
        for j in range(i + 5, i + 10):
            if 'athlete.get("name"),' in lines[j]:
                lines.insert(j + 1, '                     athlete.get("email"),\n')
                break
        break

with open("bike_analyzer/backend/db/database.py", "w") as f:
    f.writelines(lines)
print("Done")