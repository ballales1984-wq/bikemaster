import socket
import subprocess
import sys
import time

t0 = time.monotonic()

code = """
import time
t0 = time.monotonic()
from bike_analyzer.backend.api.app_factory import create_app
print(f'IMPORT done at {time.monotonic()-t0:.2f}s', flush=True)

import uvicorn
uvicorn.run(
    "bike_analyzer.backend.api.app_factory:create_app",
    factory=True,
    host="127.0.0.1",
    port=8011,
    log_config=None,
    log_level="warning",
)
"""

proc = subprocess.Popen(
    [sys.executable, "-c", code],
    stdout=sys.stdout,
    stderr=sys.stderr,
)

for i in range(120):
    time.sleep(1)
    elapsed = time.monotonic() - t0
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect(("127.0.0.1", 8011))
        s.close()
        print(f"PORT 8011 OPEN at {elapsed:.1f}s", flush=True)
        break
    except (TimeoutError, ConnectionRefusedError):
        s.close()
        if i % 5 == 0:
            print(f"  waiting... {elapsed:.1f}s", flush=True)
else:
    print(f"PORT 8011 NOT OPEN after {time.monotonic()-t0:.1f}s", flush=True)

proc.terminate()
proc.wait()
