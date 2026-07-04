import json

with open("coverage.json") as f:
    data = json.load(f)
files = data["files"]
items = [(k, v["summary"]) for k, v in files.items() if v["summary"]["num_statements"] > 20]
for k, s in sorted(items, key=lambda x: x[1]["percent_covered"]):
    print(f"{s['percent_covered']:6.1f}%  {s['num_statements']:5d} stmts  {k}")
