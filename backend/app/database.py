import os
import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.app.config import settings

logger = logging.getLogger("ecommerce.database")

db_url = settings.effective_database_url

# Handle SQLite vs PostgreSQL engine arguments and Windows paths
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    connect_args["timeout"] = 15
    # Normalize Windows relative path to absolute URL
    if "./" in db_url or not os.path.isabs(db_url.replace("sqlite:///", "")):
        raw_path = db_url.replace("sqlite:///./", "").replace("sqlite:///", "")
        abs_path = os.path.abspath(raw_path).replace("\\", "/")
        db_url = f"sqlite:///{abs_path}"

if db_url.startswith("postgresql://"):
    try:
        import psycopg  # noqa: F401
    except ImportError:
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(
    db_url,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

import datetime

def utc_now() -> datetime.datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.datetime.now(datetime.timezone.utc)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency generator for database sessions with automatic cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables defined in SQLAlchemy models."""
    from backend.app.models import (
        customer,
        product,
        order,
        inventory,
        fraud,
        shipment,
        agent_log
    )
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
