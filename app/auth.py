"""API key authentication for protected endpoints."""

from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, status

from app.dependencies import get_settings
from app.settings import Settings


async def check_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    settings: Annotated[Settings, Depends(get_settings)] = None
) -> None:
    """
    Check API key from X-API-Key header.
    
    Args:
        x_api_key: API key provided in X-API-Key header
        settings: Application settings (injected via dependency)
        
    Raises:
        HTTPException: 401 if authentication is enabled and key is missing/invalid
    """
    
    # If API key authentication is disabled, allow all requests
    if not settings.api_key_enabled:
        return
    
    # Check if API key was provided
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide via X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Validate API key
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )