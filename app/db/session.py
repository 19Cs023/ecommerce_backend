"""
Engine + session factory + the `get_db` dependency.

WHY A SESSION-PER-REQUEST PATTERN:
SQLAlchemy Sessions are NOT thread-safe and are cheap to create. The
standard pattern is: open one Session at the start of a request, use it
for every DB operation in that request, close it when the request ends
-- even if an exception was raised. FastAPI's `Depends` + generator
pattern (see `get_db` below) implements exactly this via a try/finally,
which is why you'll see `Depends(get_db)` on almost every route that
touches the database.

WHY `connect_args` FOR SQLITE:
SQLite only allows a connection to be used by the thread that created
it, by default. FastAPI can run sync code in a threadpool, so we relax
that check. This flag is a no-op (and harmless) for Postgres/MySQL.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)

# autocommit=False, autoflush=False: we want explicit control over when
# writes hit the DB (via .commit()) rather than SQLAlchemy guessing.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    FastAPI dependency. Because this is a generator, FastAPI treats the
    code after `yield` as teardown logic -- guaranteed to run even if
    the endpoint raises, closing the connection and returning it to the
    pool instead of leaking it.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
