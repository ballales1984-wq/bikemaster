import os
import socket
import subprocess
import sys
import time

os.environ["ENVIRONMENT"] = "production"
os.environ["DATABASE_URL"] = ""
os.environ["REDIS_URL"] = ""

t0 = time.monotonic()

code = '''
import time, os
t0 = time.monotonic()

# Simulate init_observability
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

print(f"OTel imports done at {time.monotonic()-t0:.3f}s", flush=True)

resource = Resource.create({"service.name": "bikemaster", "deployment.environment": "production"})
trace.set_tracer_provider(TracerProvider(resource=resource))

otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
print(f"otlp_endpoint: {otlp_endpoint}", flush=True)

otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
print(f"OTLPSpanExporter created at {time.monotonic()-t0:.3f}s", flush=True)

trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(otlp_exporter, schedule_delay_millis=5000, max_export_batch_size=100)
)
print(f"BatchSpanProcessor added at {time.monotonic()-t0:.3f}s", flush=True)

# Now import and create the app
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
