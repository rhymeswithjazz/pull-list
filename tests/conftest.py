"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture(autouse=True)
def test_environment(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-testing-only")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("KOMGA_URL", "http://localhost:25600")
    monkeypatch.setenv("KOMGA_USERNAME", "test")
    monkeypatch.setenv("KOMGA_PASSWORD", "test")


@pytest.fixture
def sample_book_data():
    """Sample Komga book API response data."""
    return {
        "id": "book-123",
        "seriesId": "series-456",
        "name": "Amazing Spider-Man 001.cbz",
        "number": "1",
        "sortNumber": 1.0,
        "sizeBytes": 50000000,
        "created": "2024-11-27T10:00:00Z",
        "lastModified": "2024-11-27T10:00:00Z",
        "fileHash": "abc123",
        "url": "/api/v1/books/book-123/file",
        "metadata": {"title": "Amazing Spider-Man #1"},
        "media": {"pagesCount": 24},
        "readProgress": None,
    }


@pytest.fixture
def sample_series_data():
    """Sample Komga series API response data."""
    return {
        "id": "series-456",
        "name": "Amazing Spider-Man",
        "booksCount": 10,
        "booksReadCount": 5,
        "booksUnreadCount": 5,
        "libraryId": "lib-001",
        "metadata": {"publisher": "Marvel"},
    }
