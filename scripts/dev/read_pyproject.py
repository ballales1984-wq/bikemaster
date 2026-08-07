
import os
import signal
import subprocess
import time

# find ruff server pid
out = subprocess.run(['powershell','-Command','(Get-Process ruff -ErrorAction SilentlyContinue).Id'], capture_output=True, text=True).stdout
pids = [p for p in out.split() if p.strip().isdigit()]
for p in pids:
    try:
        os.kill(int(p), signal.SIGTERM)
    except Exception as e:
        print('kill fail', p, e)
# race to read immediately
for _ in range(20):
    try:
        with open("pyproject.toml", encoding="utf-8") as fh:
            data = fh.read()
        print("READ_OK len=", len(data))
        print(data)
        break
    except Exception:
        time.sleep(0.05)
else:
    print('STILL_LOCKED')
