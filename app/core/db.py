from typing import Generator
from sqlmodel import Session, create_engine
from sqlalchemy.orm import scoped_session
from .config import settings

# connect_args = {"check_same_thread": False} # Specifically for sqlite
# connect_args = {}
engine = create_engine(settings.SQLALCHEMY_DATABASE_URI, pool_size=10, max_overflow=20, pool_recycle=3600)

def get_db_session() -> Generator[scoped_session, None, None]:
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()