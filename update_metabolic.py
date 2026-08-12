import re

with open("bike_analyzer/backend/db/database.py", "r", encoding="utf-8") as f:
    content = f.read()

metabolic_funcs = [
    "save_metabolic_profile",
    "get_metabolic_profile",
    "save_food_log",
    "get_food_logs_by_athlete_date",
    "update_food_log",
    "get_food_log",
    "delete_food_log",
    "save_metabolic_daily_summary",
    "get_metabolic_daily_summaries",
    "get_metabolic_daily_summary",
    "upsert_metabolic_reference_value",
    "get_metabolic_reference_value",
    "get_all_metabolic_reference_values",
    "save_metabolic_adaptive_weights",
    "get_metabolic_adaptive_weights",
]

for func in metabolic_funcs:
    old = f'@pg_dispatch("bike_analyzer.backend.db.postgres_stubs")\ndef {func}'
    new = f'@pg_dispatch("bike_analyzer.backend.db.postgres_metabolic")\ndef {func}'
    content = content.replace(old, new)

with open("bike_analyzer/backend/db/database.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated metabolic functions to postgres_metabolic")
