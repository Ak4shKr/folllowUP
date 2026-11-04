from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import settings
from app.db.session import engine

DESCRIPTION = "Single-user job outreach agent. PostgreSQL is the source of truth."


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.name,
        version=settings.version,
        description=DESCRIPTION,
        lifespan=lifespan,
    )
    app.include_router(health_router)
    return app


app = create_app()
