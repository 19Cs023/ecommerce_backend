"""
Application entrypoint. Run with:
    uvicorn app.main:app --reload

WHY `app.models` IS IMPORTED HERE (even though nothing in this file
seems to use it directly):
See the long comment in app/models/__init__.py. In short: importing
`app.models` guarantees every model class has been loaded and
registered with `Base.metadata` before `Base.metadata.create_all()`
runs below. Deleting this import would silently produce a database
missing whichever tables aren't imported elsewhere by that point --
a genuinely nasty bug to track down, since nothing raises an error.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401 -- see docstring above
from app.api.v1.api import api_router
from app.core.config import settings
from app.db.base_class import Base
from app.db.session import engine

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

# CORS: without this middleware, a browser-based frontend on a
# different origin (e.g. localhost:3000 calling localhost:8000) gets
# silently blocked by the browser's same-origin policy, even though a
# tool like curl or Postman would work fine -- CORS is enforced by
# browsers, not servers, which is why this bites people specifically
# when wiring up a frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.on_event("startup")
def on_startup() -> None:
    """
    `create_all()` is fine for local development and for this
    educational project, but it is NOT how you manage schema changes in
    production. It only ever CREATES missing tables -- it never alters
    an existing table when you add/rename/remove a column, so your code
    and your DB schema silently drift apart the moment you change a
    model after the first run. Production systems use Alembic
    migrations (`alembic upgrade head`) run explicitly as a deploy
    step, precisely so schema changes are version-controlled, reviewed,
    and reversible. This project ships an `alembic/` setup -- see
    README.md's "Migrations" section -- use that instead of relying on
    this startup hook once you're past local prototyping.
    """
    Base.metadata.create_all(bind=engine)


@app.get("/health", tags=["health"])
def health_check():
    """
    Deliberately has NO dependencies on the database, auth, or
    anything else that could fail. Load balancers and container
    orchestrators (Kubernetes liveness/readiness probes, etc.) hit this
    endpoint frequently to decide "is this instance alive?" -- if it
    depended on the DB, a DB blip would make the orchestrator kill and
    restart otherwise-healthy app instances, potentially causing an
    outage instead of just briefly degraded functionality.
    """
    return {"status": "ok"}
