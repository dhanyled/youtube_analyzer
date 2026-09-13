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
    """Initialize all tables defined in SQLModel metadata and ensure columns exist."""
    SQLModel.metadata.create_all(engine)

    # Auto-migrate SQLite schema for any newly added columns
    if str(engine.url).startswith("sqlite"):
        with engine.connect() as conn:
            # Check keywords table
            kw_cols = {
                row[1] for row in conn.exec_driver_sql("PRAGMA table_info(keywords)").fetchall()
            }
            if kw_cols:
                if "opportunity_score" not in kw_cols:
                    conn.exec_driver_sql("ALTER TABLE keywords ADD COLUMN opportunity_score FLOAT")
                if "estimated_rpm" not in kw_cols:
                    conn.exec_driver_sql("ALTER TABLE keywords ADD COLUMN estimated_rpm FLOAT")

            # Check competitors table
            comp_cols = {
                row[1] for row in conn.exec_driver_sql("PRAGMA table_info(competitors)").fetchall()
            }
            if comp_cols:
                if "views" not in comp_cols:
                    conn.exec_driver_sql("ALTER TABLE competitors ADD COLUMN views INTEGER")
                if "channel_median_views" not in comp_cols:
                    conn.exec_driver_sql(
                        "ALTER TABLE competitors ADD COLUMN channel_median_views INTEGER"
                    )
                if "outlier_score" not in comp_cols:
                    conn.exec_driver_sql("ALTER TABLE competitors ADD COLUMN outlier_score FLOAT")
                if "vph" not in comp_cols:
                    conn.exec_driver_sql("ALTER TABLE competitors ADD COLUMN vph FLOAT")

            conn.commit()


def get_session() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    with Session(engine) as session:
        yield session
