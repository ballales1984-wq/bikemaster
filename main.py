"""Bike Analyzer — GPS Analytics System for Cycling Performance

Entrypoint: starts the FastAPI application with uvicorn.
"""

import uvicorn

from backend.api.app_factory import create_app

DEFAULT_DB_URL = "sqlite:///./bike_analyzer.db"
HOST = "0.0.0.0"
PORT = 8000


def main():
    app = create_app()
    uvicorn.run(app, host=HOST, port=PORT, reload=True)


if __name__ == "__main__":
    main()
