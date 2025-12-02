"""FastAPI dependencies for authentication and authorization."""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.services.auth import decode_access_token, get_user_by_id, get_user_count


class AuthenticationRequiredError(Exception):
    """Raised when authentication is required but user is not authenticated."""

    pass


class SetupRequiredError(Exception):
    """Raised when no users exist and setup is required."""

    pass


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the current authenticated user from JWT cookie.

    Raises HTTPException with redirect to login if not authenticated.
    """
    # Check if any users exist - if not, redirect to setup
    user_count = await get_user_count(db)
    if user_count == 0:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/setup"},
        )

    token = request.cookies.get("access_token")
    if not token:
        # For HTMX requests, return 401 with HX-Redirect header
        if request.headers.get("HX-Request"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"HX-Redirect": "/login"},
            )
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"},
        )

    payload = decode_access_token(token)
    if not payload:
        # Invalid or expired token
        if request.headers.get("HX-Request"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"HX-Redirect": "/login"},
            )
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"},
        )

    user_id = int(payload.get("sub", 0))
    user = await get_user_by_id(db, user_id)

    if not user or not user.is_active:
        if request.headers.get("HX-Request"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"HX-Redirect": "/login"},
            )
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"},
        )

    return user


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Get the current user if authenticated, or None if not.

    Does not raise exceptions - useful for pages that work with or without auth.
    """
    token = request.cookies.get("access_token")
    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    user_id = int(payload.get("sub", 0))
    user = await get_user_by_id(db, user_id)

    if not user or not user.is_active:
        return None

    return user


async def require_no_users(
    db: AsyncSession = Depends(get_db),
) -> bool:
    """Dependency that ensures no users exist (for setup page).

    Raises HTTPException redirect to login if users exist.
    """
    user_count = await get_user_count(db)
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"},
        )
    return True
