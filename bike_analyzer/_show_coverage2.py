import json

with open('coverage.json') as f:
    data = json.load(f)
for path, info in sorted(data['files'].items()):
    pct = info['summary']['percent_covered']
    print(f"{pct:5.1f}%  {path}")
