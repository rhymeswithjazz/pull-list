"""Authentication service for user management and JWT tokens."""

import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import MagicLinkToken, User

settings = get_settings()


def utcnow() -> datetime:
    """Get current UTC time as naive datetime (for SQLite compatibility)."""
    return datetime.now(UTC).replace(tzinfo=None)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def create_access_token(user_id: int, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = utcnow() + expires_delta
    else:
        expire = utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    """Decode and validate a JWT access token. Returns payload or None if invalid."""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """Get a user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """Get a user by username."""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Get a user by email."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def authenticate_user(
    db: AsyncSession, username: str, password: str
) -> User | None:
    """Authenticate a user by username and password."""
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


async def create_user(
    db: AsyncSession,
    username: str,
    email: str,
    password: str,
) -> User:
    """Create a new user."""
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_count(db: AsyncSession) -> int:
    """Get the total number of users."""
    result = await db.execute(select(User))
    return len(result.scalars().all())


async def create_magic_link_token(db: AsyncSession, user_id: int) -> str:
    """Create a magic link token for a user."""
    # Generate a secure random token
    token = secrets.token_urlsafe(32)

    # Calculate expiration
    expires_at = utcnow() + timedelta(
        minutes=settings.magic_link_expire_minutes
    )

    # Store in database
    magic_token = MagicLinkToken(
        token=token,
        user_id=user_id,
        expires_at=expires_at,
    )
    db.add(magic_token)
    await db.commit()

    return token


async def verify_magic_link_token(db: AsyncSession, token: str) -> User | None:
    """Verify a magic link token and return the user if valid."""
    result = await db.execute(
        select(MagicLinkToken).where(MagicLinkToken.token == token)
    )
    magic_token = result.scalar_one_or_none()

    if not magic_token:
        return None

    # Check if already used
    if magic_token.used_at is not None:
        return None

    # Check if expired
    if magic_token.expires_at < utcnow():
        return None

    # Mark as used
    magic_token.used_at = utcnow()
    await db.commit()

    # Get the user
    user = await get_user_by_id(db, magic_token.user_id)
    if not user or not user.is_active:
        return None

    return user


async def update_user_password(db: AsyncSession, user_id: int, new_password: str) -> bool:
    """Update a user's password. Returns True if successful."""
    user = await get_user_by_id(db, user_id)
    if not user:
        return False

    user.password_hash = hash_password(new_password)
    await db.commit()
    return True


async def cleanup_expired_tokens(db: AsyncSession) -> int:
    """Delete expired magic link tokens. Returns count of deleted tokens."""
    result = await db.execute(
        select(MagicLinkToken).where(
            MagicLinkToken.expires_at < utcnow()
        )
    )
    expired_tokens = result.scalars().all()
    count = len(expired_tokens)

    for token in expired_tokens:
        await db.delete(token)

    await db.commit()
    return count
