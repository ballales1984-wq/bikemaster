import os
import socket
import subprocess
import sys
import time

os.environ["ENVIRONMENT"] = "production"
os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost:5432/nonexistent_db"
os.environ["REDIS_URL"] = ""
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4317"

t0 = time.monotonic()

code = '''
import time
t0 = time.monotonic()

from bike_analyzer.backend.api.app_factory import create_app
print(f"Full import done at {time.monotonic()-t0:.3f}s", flush=True)

app = create_app()
print(f"create_app done at {time.monotonic()-t0:.3f}s", flush=True)

import uvicorn
uvicorn.run(
    app,
    host="127.0.0.1",
    port=8012,
    log_config=None,
)
'''

proc = subprocess.Popen(
    [sys.executable, "-c", code],
    stdout=sys.stdout,
    stderr=sys.stderr,
    env=os.environ.copy(),
)

for i in range(120):
    time.sleep(1)
    elapsed = time.monotonic() - t0
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect(("127.0.0.1", 8012))
        s.close()
        print(f"PORT 8012 OPEN at {elapsed:.1f}s", flush=True)
        break
    except (TimeoutError, ConnectionRefusedError):
        s.close()
        if i % 5 == 0:
            print(f"  waiting... {elapsed:.1f}s", flush=True)
else:
    print(f"PORT 8012 NOT OPEN after {time.monotonic()-t0:.1f}s", flush=True)

proc.terminate()
proc.wait()
