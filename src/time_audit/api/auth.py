"""Authentication and authorization for the API.

This module provides JWT-based authentication for API endpoints.
Tokens are generated and verified using the secret key from configuration.
"""

from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import Depends, HTTPException, status  # type: ignore[import-untyped]
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer  # type: ignore[import-untyped]
from jose import JWTError, jwt  # type: ignore[import-untyped]

from time_audit.core.config import ConfigManager

# Security scheme for dependency injection
security = HTTPBearer()


def create_access_token(
    data: dict[str, Any], secret_key: str, expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token.

    Args:
        data: Data to encode in the token
        secret_key: Secret key for encoding
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token string

    Example:
        >>> secret_key = "your-secret-key"
        >>> token = create_access_token(
        ...     data={"sub": "user"},
        ...     secret_key=secret_key,
        ...     expires_delta=timedelta(hours=24)
        ... )
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    # Encode JWT
    encoded_jwt: str = jwt.encode(to_encode, secret_key, algorithm="HS256")
    return encoded_jwt


def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    """Verify JWT token from request.

    Args:
        credentials: HTTP authorization credentials (injected by FastAPI)

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired

    Note:
        This is a dependency function for FastAPI endpoints.
        Use with Depends(verify_token) to protect endpoints.
    """
    # Get configuration
    config = ConfigManager()

    # Check if authentication is enabled
    if not config.get("api.authentication.enabled", True):
        # Authentication disabled, return dummy payload
        return {"sub": "anonymous"}

    token = credentials.credentials
    secret_key = config.get("api.authentication.secret_key")

    if not secret_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API secret key not configured",
        )

    try:
        # Decode and verify token
        payload: dict[str, Any] = jwt.decode(token, secret_key, algorithms=["HS256"])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_token_expiry_seconds(config: ConfigManager) -> int:
    """Get token expiry time in seconds from config.

    Args:
        config: Configuration manager

    Returns:
        Token expiry in seconds
    """
    hours: int = config.get("api.authentication.token_expiry_hours", 24)
    return hours * 3600


def create_token_for_user(config: ConfigManager, user_id: str = "cli-user") -> dict[str, Any]:
    """Create a complete token response.

    Args:
        config: Configuration manager
        user_id: User identifier for the token

    Returns:
        Dictionary with access_token, token_type, and expires_in

    Example:
        >>> config = ConfigManager()
        >>> token_data = create_token_for_user(config)
        >>> print(token_data["access_token"])
    """
    # Ensure secret key exists
    secret_key = config.ensure_api_secret_key()

    # Get expiry time
    expiry_hours = config.get("api.authentication.token_expiry_hours", 24)
    expires_delta = timedelta(hours=expiry_hours)

    # Create token
    access_token = create_access_token(
        data={"sub": user_id}, secret_key=secret_key, expires_delta=expires_delta
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": get_token_expiry_seconds(config),
    }
