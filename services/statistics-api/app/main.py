"""Statistics API - Main application."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

from .config import settings
from .models import LoginEvent, LoginEventResponse, StatisticsResponse
from common.database.mongodb import connect_to_mongo, close_database_connection, get_database
import httpx
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
    description="Statistics API for device login events",
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
    "/Log/auth",
    response_model=LoginEventResponse,
    status_code=status.HTTP_200_OK,
    summary="Store login event",
    tags=["Log"]
)
async def store_login_event(
    event: LoginEvent,
    request: Request,
    current_user: dict = Depends(get_current_user)
) -> LoginEventResponse:
    """
    Store a user login event and register device.

    The userKey is extracted from the token (sub claim).
    deviceType must be one of: iOS, Android, Watch, TV.

    Calls DeviceRegistrationAPI internally using the user's token.

    Requires authentication via Keycloak.
    """
    try:
        # Extract userKey from token (sub claim)
        user_key = current_user.get("sub")
        if not user_key:
            logger.error("Token does not contain 'sub' claim")
            return LoginEventResponse(
                statusCode=400,
                message="bad_request"
            )

        # Validate deviceType against whitelist (case-insensitive)
        device_type_lower = event.deviceType.lower()
        if device_type_lower not in settings.valid_device_types:
            logger.warning(f"Invalid deviceType: {event.deviceType}")
            return LoginEventResponse(
                statusCode=400,
                message="bad_request"
            )

        # Add timestamp if not provided
        if event.timestamp is None:
            event.timestamp = datetime.utcnow()

        # Store login event in database
        db = get_database()
        collection = db["login_events"]

        document = {
            "userKey": user_key,
            "deviceType": device_type_lower,
            "timestamp": event.timestamp,
            "created_by": current_user.get("preferred_username", user_key),
            "created_at": datetime.utcnow()
        }

        result = await collection.insert_one(document)

        logger.info(
            f"Login event stored: user={user_key}, "
            f"device={event.deviceType}, id={result.inserted_id}"
        )

        # Get user's token from request
        user_token = request.headers.get("Authorization")
        if not user_token:
            logger.error("No Authorization header found")
            return LoginEventResponse(
                statusCode=400,
                message="bad_request"
            )

        # Call DeviceRegistrationAPI with user's token
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                device_response = await client.post(
                    settings.device_registration_api_url,
                    json={
                        "userKey": user_key,
                        "deviceType": event.deviceType
                    },
                    headers={
                        "Authorization": user_token
                    }
                )

                if device_response.status_code not in [200, 201]:
                    logger.warning(
                        f"DeviceRegistrationAPI returned {device_response.status_code}: "
                        f"{device_response.text}"
                    )
                    return LoginEventResponse(
                        statusCode=400,
                        message="bad_request"
                    )

                logger.info(f"Device registered successfully via DeviceRegistrationAPI for user {user_key}")

            except Exception as e:
                logger.error(f"Error calling DeviceRegistrationAPI: {e}")
                return LoginEventResponse(
                    statusCode=400,
                    message="bad_request"
                )

        return LoginEventResponse(
            statusCode=200,
            message="success"
        )

    except Exception as e:
        logger.error(f"Error storing login event: {e}")
        return LoginEventResponse(
            statusCode=400,
            message="bad_request"
        )


@app.get(
    "/Log/auth/statistics",
    response_model=StatisticsResponse,
    summary="Get device statistics",
    tags=["Log"]
)
async def get_device_statistics(
    deviceType: str,
    current_user: dict = Depends(get_current_user)
) -> StatisticsResponse:
    """
    Retrieve statistics showing count of registrations for a specific device type.

    Query parameter:
    - deviceType: The device type to query (iOS, Android, Watch, TV)

    Returns the device type and count of registrations for that type.
    Returns count=-1 if an error occurs.

    Requires authentication via Keycloak.
    """
    try:
        db = get_database()
        collection = db["login_events"]

        # Count documents matching the device type (case-insensitive)
        count = await collection.count_documents({
            "deviceType": deviceType.lower()
        })

        logger.info(f"Statistics retrieved: deviceType={deviceType}, count={count}")

        return StatisticsResponse(
            deviceType=deviceType,
            count=count
        )

    except Exception as e:
        logger.error(f"Error retrieving statistics: {e}")
        return StatisticsResponse(
            deviceType=deviceType,
            count=-1
        )


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running"
    }
