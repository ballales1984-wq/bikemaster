"""Database session management and engine configuration"""

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase

from backend.models.orm import Base


class Database:
    def __init__(self, database_url: str, echo: bool = False):
        self.engine = create_engine(database_url, echo=echo)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    def create_all(self):
        Base.metadata.create_all(bind=self.engine)

    def drop_all(self):
        Base.metadata.drop_all(bind=self.engine)

    def get_session(self) -> Session:
        return self.SessionLocal()


@lru_cache()
def get_database(database_url: str, echo: bool = False) -> Database:
    return Database(database_url, echo=echo)


def init_db(database_url: str, echo: bool = False) -> Database:
    db = get_database(database_url, echo)
    db.create_all()
    return db
