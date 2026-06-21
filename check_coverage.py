import json
with open('coverage.json') as f:
    data = json.load(f)
total = data['totals']
print(f'Total coverage: {total["percent_covered"]:.1f}%')
print(f'Target: 92%')
print(f'Gap: {92 - total["percent_covered"]:.1f}%')
print()
files = data['files']
for path, info in sorted(files.items(), key=lambda x: x[1]['summary']['percent_covered']):
    if 'services' in path or 'repositories' in path:
        pct = info['summary']['percent_covered']
        print(f'{pct:.1f}%  {path}')
