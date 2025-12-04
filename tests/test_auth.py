"""Tests for authentication service - password hashing and JWT tokens."""

from datetime import timedelta

import pytest

from app.services.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password_returns_string(self):
        """hash_password should return a string."""
        hashed = hash_password("password123")
        assert isinstance(hashed, str)

    def test_hash_password_not_plaintext(self):
        """Hashed password should not equal the plaintext."""
        password = "mySecretPassword"
        hashed = hash_password(password)
        assert hashed != password

    def test_hash_password_is_bcrypt_format(self):
        """Hashed password should be in bcrypt format."""
        hashed = hash_password("password")
        # bcrypt hashes start with $2a$, $2b$, or $2y$ and are 60 chars
        assert hashed.startswith(("$2a$", "$2b$", "$2y$"))
        assert len(hashed) == 60

    def test_hash_password_different_each_time(self):
        """Same password should produce different hashes (due to salt)."""
        password = "samePassword"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """verify_password should return True for correct password."""
        password = "correctPassword123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """verify_password should return False for wrong password."""
        password = "correctPassword"
        wrong_password = "wrongPassword"
        hashed = hash_password(password)
        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_case_sensitive(self):
        """Password verification should be case-sensitive."""
        password = "CaseSensitive"
        hashed = hash_password(password)
        assert verify_password("casesensitive", hashed) is False
        assert verify_password("CASESENSITIVE", hashed) is False

    def test_verify_password_empty_wrong(self):
        """Empty password should not verify against a hashed password."""
        password = "notEmpty"
        hashed = hash_password(password)
        assert verify_password("", hashed) is False

    def test_hash_and_verify_special_characters(self):
        """Should handle passwords with special characters."""
        password = "p@$$w0rd!#$%^&*()_+-=[]{}|;':\",./<>?"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_hash_and_verify_unicode(self):
        """Should handle passwords with unicode characters."""
        password = "パスワード123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_hash_and_verify_max_length_password(self):
        """Should handle passwords at bcrypt's 72-byte limit."""
        password = "a" * 72
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_hash_password_rejects_too_long(self):
        """Passwords over 72 bytes should raise ValueError.

        Note: This documents current behavior. Production code may want to
        truncate passwords before hashing to handle this gracefully.
        """
        password = "a" * 100
        with pytest.raises(ValueError, match="password cannot be longer than 72 bytes"):
            hash_password(password)


class TestJwtTokens:
    """Tests for JWT token creation and validation."""

    def test_create_access_token_returns_string(self):
        """create_access_token should return a string."""
        token = create_access_token(user_id=1)
        assert isinstance(token, str)

    def test_create_access_token_is_jwt_format(self):
        """Token should be in JWT format (3 parts separated by dots)."""
        token = create_access_token(user_id=1)
        parts = token.split(".")
        assert len(parts) == 3

    def test_decode_access_token_valid(self):
        """decode_access_token should return payload for valid token."""
        token = create_access_token(user_id=42)
        payload = decode_access_token(token)

        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["type"] == "access"

    def test_decode_access_token_invalid(self):
        """decode_access_token should return None for invalid token."""
        payload = decode_access_token("invalid.token.here")
        assert payload is None

    def test_decode_access_token_tampered(self):
        """decode_access_token should return None for tampered token."""
        token = create_access_token(user_id=1)
        # Tamper with the token
        tampered = token[:-5] + "XXXXX"
        payload = decode_access_token(tampered)
        assert payload is None

    def test_decode_access_token_wrong_type(self):
        """decode_access_token should return None if type is not 'access'."""
        # Create a token manually with wrong type
        from jose import jwt

        from app.config import get_settings

        settings = get_settings()
        wrong_type_token = jwt.encode(
            {"sub": "1", "type": "refresh", "exp": 9999999999},
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )
        payload = decode_access_token(wrong_type_token)
        assert payload is None

    def test_create_access_token_with_custom_expiry(self):
        """Token should use custom expiry when provided."""
        token = create_access_token(user_id=1, expires_delta=timedelta(hours=24))
        payload = decode_access_token(token)
        assert payload is not None

    def test_decode_access_token_expired(self):
        """decode_access_token should return None for expired token."""
        # Create a token that's already expired
        token = create_access_token(user_id=1, expires_delta=timedelta(seconds=-1))
        payload = decode_access_token(token)
        assert payload is None

    def test_token_contains_user_id(self):
        """Token payload should contain the user ID."""
        user_id = 123
        token = create_access_token(user_id=user_id)
        payload = decode_access_token(token)

        assert payload is not None
        assert payload["sub"] == str(user_id)

    def test_different_users_different_tokens(self):
        """Different user IDs should produce different tokens."""
        token1 = create_access_token(user_id=1)
        token2 = create_access_token(user_id=2)
        assert token1 != token2

    def test_decode_empty_token(self):
        """decode_access_token should handle empty string."""
        payload = decode_access_token("")
        assert payload is None

    def test_decode_none_like_token(self):
        """decode_access_token should handle None-like values."""
        payload = decode_access_token("null")
        assert payload is None
