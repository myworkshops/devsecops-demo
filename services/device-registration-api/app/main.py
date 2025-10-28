"""Device Registration API - Main application."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

from .config import settings
from .models import DeviceRegistration, DeviceRegistrationResponse
from common.database.mongodb import connect_to_mongo, close_database_connection, get_database
from common.auth.keycloak import KeycloakConfig, verify_token, require_role, get_current_user
from common.health.checks import health_check, readiness_check, liveness_check

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Initialize Keycloak
    KeycloakConfig.initialize(
        server_url=settings.keycloak_server_url,
        realm=settings.keycloak_realm,
        client_id=settings.keycloak_client_id
    )

    # Connect to MongoDB
    await connect_to_mongo(
        mongo_uri=settings.mongodb_uri,
        database_name=settings.mongodb_database
    )

    logger.info(f"{settings.app_name} started successfully")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")
    await close_database_connection()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Device Registration API for managing user devices",
    lifespan=lifespan
)

# Custom middleware to handle OPTIONS requests
class CORSPreflightMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        if request.method == "OPTIONS":
            origin = request.headers.get("origin", "")
            if origin in [o.strip() for o in settings.cors_origins.split(',')]:
                return JSONResponse(
                    content={},
                    status_code=200,
                    headers={
                        "Access-Control-Allow-Origin": origin,
                        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                        "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
                        "Access-Control-Allow-Credentials": "true",
                        "Access-Control-Max-Age": "3600",
                    }
                )
        response = await call_next(request)
        return response

# Configure CORS
cors_origins = [origin.strip() for origin in settings.cors_origins.split(',')]
logger.info(f"CORS origins configured: {cors_origins}")

# Add custom OPTIONS handler first
app.add_middleware(CORSPreflightMiddleware)

# Then add standard CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
    max_age=3600,
)


# Health check endpoints
@app.get("/health", include_in_schema=False)
async def health():
    """Health check endpoint."""
    return await health_check(service_name=settings.app_name)


@app.get("/ready", include_in_schema=False)
async def ready():
    """Readiness check endpoint."""
    return await readiness_check()


@app.get("/live", include_in_schema=False)
async def live():
    """Liveness check endpoint."""
    return await liveness_check()


# API Endpoints
@app.post(
    "/Device/register",
    response_model=DeviceRegistrationResponse,
    status_code=status.HTTP_200_OK,
    summary="Register a device",
    tags=["Device"]
)
async def register_device(
    registration: DeviceRegistration,
    current_user: dict = Depends(get_current_user)
) -> DeviceRegistrationResponse:
    """
    Register a device type for a user.

    Receives userKey and deviceType, stores the registration in the database.

    Returns statusCode 200 on success or 400 on failure.

    Requires valid authentication token from Keycloak.
    This endpoint is only accessible internally (ClusterIP service).
    """
    try:
        db = get_database()
        collection = db["device_registrations"]

        # Check if device already registered for this user
        existing = await collection.find_one({
            "userKey": registration.userKey,
            "deviceType": registration.deviceType.lower()
        })

        if existing:
            logger.warning(
                f"Device already registered: user={registration.userKey}, "
                f"device={registration.deviceType}"
            )
            return DeviceRegistrationResponse(statusCode=400)

        # Prepare document
        document = {
            "userKey": registration.userKey,
            "deviceType": registration.deviceType.lower(),
            "device_name": registration.device_name,
            "registered_by": current_user.get("username"),
            "registered_at": datetime.utcnow()
        }

        # Insert into database
        result = await collection.insert_one(document)

        logger.info(
            f"Device registered: user={registration.userKey}, "
            f"device={registration.deviceType}, id={result.inserted_id}"
        )

        return DeviceRegistrationResponse(statusCode=200)

    except Exception as e:
        logger.error(f"Error registering device: {e}")
        return DeviceRegistrationResponse(statusCode=400)


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running"
    }
