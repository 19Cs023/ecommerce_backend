"""
Shared pytest fixtures.

WHY AN IN-MEMORY SQLITE DB FOR TESTS (instead of hitting the real dev
DB, or mocking the DB entirely):
- Mocking the ORM layer means your tests verify "did I call the mock
  correctly", not "does this SQL actually do what I think" -- bugs in
  query logic sail straight through.
- Hitting the real Postgres dev DB makes tests slow, stateful (test A
  leaves rows that break test B), and unable to run in parallel.
- An in-memory SQLite DB, recreated fresh for every single test
  function, gives you real SQL execution with zero cross-test
  contamination and near-instant setup/teardown.

WHY `StaticPool` IS REQUIRED HERE SPECIFICALLY FOR SQLITE IN-MEMORY:
Every new connection to `sqlite:///:memory:` normally gets its OWN
private, empty database -- fine for a script, useless for a web app
where the request handler's connection and the test's setup connection
must see the SAME data. `StaticPool` forces every connection from this
engine to reuse a single underlying connection, so writes made via one
"connection" are visible to reads via another within the same test.

`app.dependency_overrides[get_db] = override_get_db` is FastAPI's
built-in mechanism for swapping a dependency during tests without
touching a single line of route/application code -- the routes still
just say `Depends(get_db)`; only the test process's resolution of that
dependency changes.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401 -- registers all tables on Base.metadata
from app.db.base_class import Base
from app.db.session import get_db
from app.main import app

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture()
def db_session():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # db_session fixture owns closing the session, not this override

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
