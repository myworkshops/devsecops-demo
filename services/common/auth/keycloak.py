"""Keycloak OIDC authentication and authorization."""

import logging
from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
import httpx

logger = logging.getLogger(__name__)

security = HTTPBearer()


class KeycloakConfig:
    """Keycloak configuration."""

    def __init__(
        self,
        server_url: str,
        realm: str,
        client_id: str,
    ):
        self.server_url = server_url.rstrip('/')
        self.realm = realm
        self.client_id = client_id
        self.jwks_uri = f"{self.server_url}/realms/{realm}/protocol/openid-connect/certs"
        self.issuer = f"{self.server_url}/realms/{realm}"

    _instance: Optional['KeycloakConfig'] = None

    @classmethod
    def initialize(cls, server_url: str, realm: str, client_id: str) -> None:
        """Initialize the Keycloak configuration."""
        cls._instance = cls(server_url, realm, client_id)
        logger.info(f"Keycloak configured: {server_url}/realms/{realm}")

    @classmethod
    def get(cls) -> 'KeycloakConfig':
        """Get the Keycloak configuration instance."""
        if cls._instance is None:
            raise RuntimeError("KeycloakConfig not initialized. Call initialize() first.")
        return cls._instance


async def get_jwks() -> dict:
    """
    Fetch JSON Web Key Set from Keycloak.

    Returns:
        dict: JWKS data
    """
    config = KeycloakConfig.get()
    async with httpx.AsyncClient() as client:
        response = await client.get(config.jwks_uri)
        response.raise_for_status()
        return response.json()


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Verify JWT token from Keycloak.

    Args:
        credentials: HTTP Authorization credentials

    Returns:
        dict: Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials
    config = KeycloakConfig.get()

    try:
        # Get JWKS
        jwks = await get_jwks()

        # Decode and verify token
        unverified_header = jwt.get_unverified_header(token)

        # Find the correct key
        rsa_key = None
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = key
                break

        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find appropriate key",
            )

        # Verify token
        # For public clients, audience and issuer validation are optional
        # The token issuer may be the public URL (e.g., keycloak.local)
        # while the API uses internal URL (e.g., keycloak.keycloak.svc.cluster.local)
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            options={"verify_aud": False, "verify_iss": False}
        )

        # Manually verify the realm matches
        if "iss" in payload:
            token_realm = payload["iss"].split("/realms/")[-1] if "/realms/" in payload["iss"] else None
            if token_realm != config.realm:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid realm: expected {config.realm}, got {token_realm}",
                )

        return payload

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except JWTError as e:
        logger.error(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


def require_role(required_roles: List[str]):
    """
    Dependency to require specific roles.

    Args:
        required_roles: List of required roles (e.g., ['admin', 'operator'])

    Returns:
        Callable: FastAPI dependency function
    """
    async def role_checker(token_payload: dict = Depends(verify_token)) -> dict:
        """
        Check if user has required role.

        Args:
            token_payload: Decoded JWT token

        Returns:
            dict: Token payload if authorized

        Raises:
            HTTPException: If user doesn't have required role
        """
        # Get roles from token
        realm_access = token_payload.get("realm_access", {})
        user_roles = realm_access.get("roles", [])

        # Check if user has any of the required roles
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {', '.join(required_roles)}",
            )

        return token_payload

    return role_checker


async def get_current_user(token_payload: dict = Depends(verify_token)) -> dict:
    """
    Get current authenticated user information.

    Args:
        token_payload: Decoded JWT token

    Returns:
        dict: User information
    """
    return {
        "username": token_payload.get("preferred_username"),
        "email": token_payload.get("email"),
        "roles": token_payload.get("realm_access", {}).get("roles", []),
        "sub": token_payload.get("sub"),
    }
