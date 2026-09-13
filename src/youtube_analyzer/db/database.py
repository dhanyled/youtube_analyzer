"""Database connection and session management."""

import os
from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

DEFAULT_DB_URL = "sqlite:///youtube_analyzer.db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    connect_args=connect_args,
)


def init_db() -> None:
    """Initialize all tables defined in SQLModel metadata."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    with Session(engine) as session:
        yield session
