
import os
import signal
import subprocess
import time

out = subprocess.run(['powershell','-Command','(Get-Process ruff -ErrorAction SilentlyContinue).Id'], capture_output=True, text=True).stdout
for p in out.split():
    if p.strip().isdigit():
        try:
            os.kill(int(p), signal.SIGTERM)
        except Exception as e:
            print("kill", p, e)
time.sleep(0.1)
for f in ['bike_analyzer/backend/settings.py','bike_analyzer/backend/app_factory.py','bike_analyzer/backend/api/routes.py']:
    print(f, os.access(f, os.R_OK))

