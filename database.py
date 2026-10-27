"""
OpsCommand — Database Engine Configuration
===========================================
High-performance SQLite engine configured with Write-Ahead Logging (WAL) mode,
connection pooling, 64MB memory page cache, and foreign key enforcement.

PostgreSQL-ready: simply change DATABASE_URL in config.py or your .env file.
"""
import os
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker, declarative_base
import config

DATABASE_URL = config.DATABASE_URL

# Extract local path if using sqlite
if DATABASE_URL.startswith("sqlite:///"):
    DB_PATH = DATABASE_URL.replace("sqlite:///", "")
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
        pool_pre_ping=True,
    )

    @sa_event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        """Optimise SQLite for high-concurrency operational workloads."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA cache_size=-64000")   # 64 MB page cache
        cursor.execute("PRAGMA busy_timeout=5000")    # 5 s lock wait timeout
        cursor.close()
else:
    # Generic PostgreSQL / MySQL engine
    DB_PATH = None
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database and create all tables defined by ORM models."""
    import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
