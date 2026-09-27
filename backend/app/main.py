"""
Application entrypoint.

v0.1 wires up: settings, structured logging, CORS, and the health/readiness
router. Feature routers (auth, collections, documents, conversations, rag)
are added in later versions as `app/<feature>/router.py` and included here
under `settings.api_prefix` — none exist yet, deliberately.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.auth.router import router as auth_router
from app.collections.router import router as collections_router
from app.core.config import get_settings
from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    logger.info(
        "application_startup",
        extra={"environment": settings.environment, "app_name": settings.app_name},
    )
    yield
    logger.info("application_shutdown")


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health/readiness are mounted at the root, not under /api/v1 — most
# orchestrators (Docker healthchecks, k8s probes, load balancers) expect
# an unversioned, stable path.
app.include_router(health_router)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(collections_router, prefix=settings.api_prefix)
