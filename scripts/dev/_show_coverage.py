import json

with open('coverage.json') as f:
    data = json.load(f)
files = data['files']
for path, info in sorted(files.items(), key=lambda x: x[1]['summary']['percent_covered']):
    pct = info['summary']['percent_covered']
    print(f"{pct:5.1f}%  {path}")
