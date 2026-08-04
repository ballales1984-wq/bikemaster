import subprocess, json, os

env = dict(os.environ)
result = subprocess.run(
    ["npx", "eslint", ".", "--ext", ".vue,.ts,.js", "--max-warnings=5000", "-f", "json"],
    capture_output=True, text=True, timeout=90, cwd="D:/BikeMaster/frontend"
)
data = json.loads(result.stdout)
for item in data:
    if item.get("errorCount", 0) > 0:
        print(f"{item['errorCount']} errors: {item['filePath']}")
