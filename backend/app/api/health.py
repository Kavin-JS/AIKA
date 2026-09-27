"""
Health and readiness endpoints.

These two are deliberately different:

- /health/live  — "is the process up at all?" Never touches the database.
  Used by orchestrators to decide whether to restart the container.
- /health/ready — "can this instance actually serve traffic?" Checks the
  database connection. Used by orchestrators/load balancers to decide
  whether to route requests to this instance.

Conflating the two is a common production bug: a liveness check that
depends on the database will cause a restart loop during a brief DB
blip, instead of just pulling the instance out of rotation.
"""

import logging

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def readiness(db: Session = Depends(get_db)) -> JSONResponse:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("readiness_check_failed")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unavailable", "database": "unreachable"},
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "ok", "database": "reachable"},
    )
