"""FastAPI dependencies for database access"""

from typing import Generator

from sqlalchemy.orm import Session

from backend.db.session import get_database

DEFAULT_DB_URL = "sqlite:///./bike_analyzer.db"


def get_db(db_url: str = DEFAULT_DB_URL) -> Generator[Session, None, None]:
    db = get_database(db_url)
    session = db.get_session()
    try:
        yield session
    finally:
        session.close()
