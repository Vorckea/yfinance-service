"""API key authentication for protected endpoints."""

from logging import getLogger

from fastapi import Depends, Header, HTTPException, Request, status
from typing_extensions import Annotated

from app.dependencies import get_settings
from app.settings import Settings

logger = getLogger(__name__)


async def check_api_key(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    """Check API key from X-API-Key header.

    Args:
        request: The FastAPI request object
        x_api_key: API key provided in X-API-Key header
        settings: Application settings

    Raises:
        HTTPException: 401 if authentication is enabled and key is missing/invalid

    """
    # If API key authentication is disabled or endpoint is not protected, allow request
    endpoint = request.url.path.split("/")[1] if len(request.url.path.split("/")) > 1 else "root"
    if not settings.api_key_enabled or endpoint in settings.api_key_unprotected_endpoints:
        return

    # Check if API key was provided
    if not x_api_key:
        logger.warning("Missing API key", extra={"endpoint": endpoint})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide via X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Validate API key
    if x_api_key != settings.api_key:
        logger.warning("Invalid API key", extra={"endpoint": endpoint})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    logger.info("Authentication passed", extra={"endpoint": endpoint})
