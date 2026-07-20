import logging
import os
import sys

log_dir = r"D:\BikeMaster"
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, "backend-oauth.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.FileHandler(log_path, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

# Reduce noisy libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

os.environ.setdefault("PYTHONPATH", r"D:\BikeMaster")
os.chdir(r"D:\BikeMaster")

import uvicorn

uvicorn.run(
    "bike_analyzer.backend.api.app_factory:create_app",
    factory=True,
    app_dir=r"D:\BikeMaster",
    host="0.0.0.0",
    port=8000,
    log_level="info",
)
