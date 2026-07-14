
import os, signal, subprocess, time
out = subprocess.run(['powershell','-Command','(Get-Process ruff,jedi -ErrorAction SilentlyContinue).Id'], capture_output=True, text=True).stdout
for p in out.split():
    if p.strip().isdigit():
        try: os.kill(int(p), signal.SIGTERM)
        except Exception as e: print('kill',p,e)
for _ in range(10):
    res=[(f, os.access(f, os.R_OK)) for f in ['bike_analyzer/backend/settings.py','bike_analyzer/backend/app_factory.py','bike_analyzer/backend/api/routes.py','pyproject.toml']]
    print(res)
    time.sleep(0.3)

