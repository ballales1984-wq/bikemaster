import os, tempfile, sys
env = {
    "SECRET_KEY": "test-secret-key-for-jwt-testing-123456",
    "ALGORITHM": "HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
    "JWT_ISSUER": "test-issuer",
    "JWT_AUDIENCE": "test-audience",
    "GROQ_API_KEY": "test-key-for-unit-tests",
    "GOOGLE_MAPS_API_KEY": "",
    "SENTRY_DSN": "",
    "ENVIRONMENT": "test",
    "WEATHER_API_KEY": "",
    "GOOGLE_CLIENT_ID": "",
    "GOOGLE_CLIENT_SECRET": "",
}
os.environ.update(env)
sys.path.insert(0, ".")

from io import BytesIO
from starlette.testclient import TestClient
from bike_analyzer.backend.api.app_factory import create_app
from bike_analyzer.backend.db import database as db_mod
from bike_analyzer.backend.security import create_access_token

p = os.path.join(tempfile.gettempdir(), "gpxdiag.db")
for s in ("", "-wal", "-shm"):
    try:
        os.unlink(p + s)
    except OSError:
        pass
os.environ["DB_PATH"] = p
db_mod.DB_PATH = p
db_mod.init_db()
app = create_app()
tc = TestClient(app)
tc.headers["Authorization"] = "Bearer " + create_access_token(subject="0", is_admin=True)

gpx_content = '''<?xml version="1.0"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>
<trkpt lat="45.0" lon="7.0"><time>2024-06-15T10:00:00Z</time></trkpt>
<trkpt lat="45.001" lon="7.001"><time>2024-06-15T10:30:00Z</time></trkpt>
</trkseg></trk></gpx>'''
files = {"file": ("test.gpx", BytesIO(gpx_content.encode()), "application/gpx+xml")}
r = tc.post("/api/v1/import/gpx", files=files)
print("STATUS", r.status_code)
print(r.text[:1500])
