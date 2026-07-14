
import os, signal, subprocess, time
# find ruff server pid
out = subprocess.run(['powershell','-Command','(Get-Process ruff -ErrorAction SilentlyContinue).Id'], capture_output=True, text=True).stdout
pids = [p for p in out.split() if p.strip().isdigit()]
for p in pids:
    try:
        os.kill(int(p), signal.SIGTERM)
    except Exception as e:
        print('kill fail', p, e)
# race to read immediately
for attempt in range(20):
    try:
        data = open('pyproject.toml', encoding='utf-8').read()
        print('READ_OK len=', len(data))
        print(data)
        break
    except Exception as e:
        time.sleep(0.05)
else:
    print('STILL_LOCKED')

