"""
Database connection and session factory.
Supports both SQLite (default for instant local run) and PostgreSQL (for production).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config.settings import settings

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    # Ensure new columns exist on legacy SQLite databases without wiping data
    from sqlalchemy import text
    with engine.connect() as conn:
        migrations = [
            ("jobs", "user_id", "INTEGER"),
            ("applications", "user_id", "INTEGER"),
            ("user_profiles", "search_preferences", "JSON"),
            ("user_profiles", "api_keys", "JSON")
        ]
        for table, col, col_type in migrations:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                conn.commit()
            except Exception:
                pass # Column already exists
