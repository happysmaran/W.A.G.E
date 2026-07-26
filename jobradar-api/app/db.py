from __future__ import annotations

from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = "sqlite:///./WAGE.db"

# check_same_thread=False is safe here because FastAPI's default dependency
# injection opens/closes a fresh session per request rather than sharing one
# across threads.
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
