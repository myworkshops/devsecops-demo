"""Health check implementations."""

import logging
from typing import Dict
from fastapi import status
from fastapi.responses import JSONResponse
from ..database.mongodb import get_database

logger = logging.getLogger(__name__)


async def health_check(service_name: str = "unknown") -> JSONResponse:
    """
    Basic health check endpoint.

    Args:
        service_name: Name of the service

    Returns:
        JSONResponse: Health status
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "healthy", "service": service_name}
    )


async def readiness_check() -> JSONResponse:
    """
    Readiness check - verifies service is ready to accept traffic.
    Checks database connectivity.

    Returns:
        JSONResponse: Readiness status
    """
    checks = {}
    all_ready = True

    # Check MongoDB connection
    try:
        db = get_database()
        await db.command('ping')
        checks["mongodb"] = "ready"
    except Exception as e:
        logger.error(f"MongoDB readiness check failed: {e}")
        checks["mongodb"] = "not ready"
        all_ready = False

    status_code = status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_ready else "not ready",
            "checks": checks
        }
    )


async def liveness_check() -> JSONResponse:
    """
    Liveness check - verifies service is alive.

    Returns:
        JSONResponse: Liveness status
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "alive"}
    )
