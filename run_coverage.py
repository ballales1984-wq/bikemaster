import subprocess, json, re
result = subprocess.run(
    ["python", "-m", "pytest", "tests/", "--cov=bike_analyzer", "--cov-report=term-missing", "--no-header", "-q", "--timeout=60"],
    capture_output=True, text=True, timeout=300
)
# Parse coverage from output
lines = result.stdout.split("\n")
for line in lines:
    if "%" in line and ("bike_analyzer" in line or "TOTAL" in line):
        print(line)
# Print last 10 lines for summary
print("\n=== LAST 10 LINES ===")
for line in lines[-10:]:
    print(line)
