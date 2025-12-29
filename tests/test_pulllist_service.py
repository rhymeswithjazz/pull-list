"""Tests for PullListService - generate_pulllist with mocked dependencies."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.komga import KomgaBook
from app.services.pulllist import PullListService, get_current_week_id


def make_mock_book(
    book_id: str,
    series_id: str,
    number: str = "1",
    created_date: datetime | None = None,
    is_read: bool = False,
) -> KomgaBook:
    """Create a mock KomgaBook for testing."""
    if created_date is None:
        created_date = datetime.now(UTC)

    return KomgaBook(
        id=book_id,
        series_id=series_id,
        name=f"Book {number}.cbz",
        number=number,
        sort_number=float(number) if number.isdigit() else 1.0,
        size_bytes=50000000,
        created_date=created_date,
        last_modified_date=created_date,
        file_hash="abc123",
        url=f"/api/v1/books/{book_id}/file",
        metadata={"title": f"Book #{number}"},
        read_progress={"completed": is_read} if is_read else None,
        pages_count=24,
    )


def make_mock_tracked_series(
    series_id: int,
    komga_series_id: str,
    name: str,
    mylar_comic_id: str | None = None,
    is_active: bool = True,
) -> MagicMock:
    """Create a mock TrackedSeries for testing."""
    series = MagicMock()
    series.id = series_id
    series.komga_series_id = komga_series_id
    series.name = name
    series.mylar_comic_id = mylar_comic_id
    series.is_active = is_active
    return series


class TestGeneratePulllistEmptyTracked:
    """Tests for generate_pulllist when no series are tracked."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock()
        return db

    async def test_empty_tracked_series_returns_empty_result(self, mock_db):
        """When no series are tracked, should return empty result."""
        # Mock execute to return empty list for tracked series query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        service = PullListService(mock_db)
        result = await service.generate_pulllist()

        assert result.success is True
        assert result.items == []
        assert result.readlist_id is None
        assert result.error is None

    async def test_empty_tracked_records_run(self, mock_db):
        """Empty result should still record the run."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        service = PullListService(mock_db)
        await service.generate_pulllist()

        # Should have added a run record
        assert mock_db.add.called
        assert mock_db.commit.call_count >= 1


class TestGeneratePulllistWithBooks:
    """Tests for generate_pulllist with tracked series and books."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    async def test_finds_recent_books(self, mock_db):
        """Should find books created within days_back period."""
        # Setup tracked series
        tracked_series = [
            make_mock_tracked_series(1, "series-1", "Spider-Man"),
        ]

        # Mock execute calls
        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # First call: get tracked series
                result.scalars.return_value.all.return_value = tracked_series
            else:
                # Other calls: check for existing weekly books
                result.scalar_one_or_none.return_value = None
            return result

        mock_db.execute = mock_execute

        # Mock Komga client
        recent_book = make_mock_book(
            "book-1", "series-1", "1", datetime.now(UTC) - timedelta(days=1)
        )

        with patch("app.services.pulllist.KomgaClient") as mock_komga_cls:
            mock_komga = AsyncMock()
            mock_komga.get_series_books = AsyncMock(return_value=[recent_book])
            mock_komga.get_book_read_url = MagicMock(
                return_value="http://localhost/book/book-1/read"
            )
            mock_komga.find_readlist_by_name = AsyncMock(return_value=None)
            mock_komga.create_readlist = AsyncMock(return_value={"id": "readlist-1"})
            mock_komga_cls.return_value.__aenter__.return_value = mock_komga

            with patch("app.services.pulllist.MylarClient") as mock_mylar_cls:
                mock_mylar = AsyncMock()
                mock_mylar.test_connection = AsyncMock(return_value=False)
                mock_mylar_cls.return_value.__aenter__.return_value = mock_mylar

                service = PullListService(mock_db)
                result = await service.generate_pulllist()

        assert result.success is True
        assert len(result.items) == 1
        assert result.items[0].komga_book_id == "book-1"
        assert result.items[0].series_name == "Spider-Man"

    async def test_filters_old_books(self, mock_db):
        """Should not include books older than days_back."""
        tracked_series = [
            make_mock_tracked_series(1, "series-1", "Spider-Man"),
        ]

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalars.return_value.all.return_value = tracked_series
            else:
                result.scalar_one_or_none.return_value = None
            return result

        mock_db.execute = mock_execute

        # Book created 30 days ago (outside 7-day window)
        old_book = make_mock_book("book-1", "series-1", "1", datetime.now(UTC) - timedelta(days=30))

        with patch("app.services.pulllist.KomgaClient") as mock_komga_cls:
            mock_komga = AsyncMock()
            mock_komga.get_series_books = AsyncMock(return_value=[old_book])
            mock_komga.get_book_read_url = MagicMock(return_value="http://localhost/read")
            mock_komga_cls.return_value.__aenter__.return_value = mock_komga

            with patch("app.services.pulllist.MylarClient") as mock_mylar_cls:
                mock_mylar = AsyncMock()
                mock_mylar.test_connection = AsyncMock(return_value=False)
                mock_mylar_cls.return_value.__aenter__.return_value = mock_mylar

                service = PullListService(mock_db)
                result = await service.generate_pulllist(days_back=7)

        assert result.success is True
        assert len(result.items) == 0

    async def test_mylar_failure_does_not_break_pulllist(self, mock_db):
        """Mylar connection failure should not affect Komga books."""
        tracked_series = [
            make_mock_tracked_series(1, "series-1", "Spider-Man"),
        ]

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalars.return_value.all.return_value = tracked_series
            else:
                result.scalar_one_or_none.return_value = None
            return result

        mock_db.execute = mock_execute

        recent_book = make_mock_book(
            "book-1", "series-1", "1", datetime.now(UTC) - timedelta(days=1)
        )

        with patch("app.services.pulllist.KomgaClient") as mock_komga_cls:
            mock_komga = AsyncMock()
            mock_komga.get_series_books = AsyncMock(return_value=[recent_book])
            mock_komga.get_book_read_url = MagicMock(return_value="http://localhost/read")
            mock_komga.find_readlist_by_name = AsyncMock(return_value=None)
            mock_komga.create_readlist = AsyncMock(return_value={"id": "readlist-1"})
            mock_komga_cls.return_value.__aenter__.return_value = mock_komga

            with patch("app.services.pulllist.MylarClient") as mock_mylar_cls:
                # Mylar raises an exception
                mock_mylar_cls.return_value.__aenter__.side_effect = Exception("Connection failed")

                service = PullListService(mock_db)
                result = await service.generate_pulllist()

        # Should still succeed with Komga books
        assert result.success is True
        assert len(result.items) == 1

    async def test_creates_readlist_with_current_week_books(self, mock_db):
        """Should only include current week's books in readlist."""
        tracked_series = [
            make_mock_tracked_series(1, "series-1", "Spider-Man"),
        ]

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalars.return_value.all.return_value = tracked_series
            else:
                result.scalar_one_or_none.return_value = None
            return result

        mock_db.execute = mock_execute

        recent_book = make_mock_book("book-1", "series-1", "1", datetime.now(UTC))

        with patch("app.services.pulllist.KomgaClient") as mock_komga_cls:
            mock_komga = AsyncMock()
            mock_komga.get_series_books = AsyncMock(return_value=[recent_book])
            mock_komga.get_book_read_url = MagicMock(return_value="http://localhost/read")
            mock_komga.find_readlist_by_name = AsyncMock(return_value=None)
            mock_komga.create_readlist = AsyncMock(return_value={"id": "readlist-1"})
            mock_komga_cls.return_value.__aenter__.return_value = mock_komga

            with patch("app.services.pulllist.MylarClient") as mock_mylar_cls:
                mock_mylar = AsyncMock()
                mock_mylar.test_connection = AsyncMock(return_value=False)
                mock_mylar_cls.return_value.__aenter__.return_value = mock_mylar

                service = PullListService(mock_db)
                result = await service.generate_pulllist(create_readlist=True)

        assert result.readlist_id == "readlist-1"
        current_week = get_current_week_id()
        assert result.readlist_name == f"Pull List - {current_week}"
        mock_komga.create_readlist.assert_called_once()

    async def test_deletes_existing_readlist_before_creating(self, mock_db):
        """Should update existing readlist with same name instead of recreating."""
        tracked_series = [
            make_mock_tracked_series(1, "series-1", "Spider-Man"),
        ]

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalars.return_value.all.return_value = tracked_series
            else:
                result.scalar_one_or_none.return_value = None
            return result

        mock_db.execute = mock_execute

        recent_book = make_mock_book("book-1", "series-1", "1", datetime.now(UTC))

        with patch("app.services.pulllist.KomgaClient") as mock_komga_cls:
            mock_komga = AsyncMock()
            mock_komga.get_series_books = AsyncMock(return_value=[recent_book])
            mock_komga.get_book_read_url = MagicMock(return_value="http://localhost/read")
            # Return existing readlist
            mock_komga.find_readlist_by_name = AsyncMock(
                return_value={"id": "existing-readlist", "name": "Pull List - 2024-W48"}
            )
            mock_komga.update_readlist = AsyncMock(return_value={"id": "existing-readlist"})
            mock_komga.create_readlist = AsyncMock(return_value={"id": "new-readlist"})
            mock_komga_cls.return_value.__aenter__.return_value = mock_komga

            with patch("app.services.pulllist.MylarClient") as mock_mylar_cls:
                mock_mylar = AsyncMock()
                mock_mylar.test_connection = AsyncMock(return_value=False)
                mock_mylar_cls.return_value.__aenter__.return_value = mock_mylar

                service = PullListService(mock_db)
                result = await service.generate_pulllist(create_readlist=True)

        # Should have updated existing readlist, not deleted or created new one
        mock_komga.update_readlist.assert_called_once()
        mock_komga.create_readlist.assert_not_called()
        assert result.readlist_id == "existing-readlist"

    async def test_skips_readlist_when_disabled(self, mock_db):
        """Should not create readlist when create_readlist=False."""
        tracked_series = [
            make_mock_tracked_series(1, "series-1", "Spider-Man"),
        ]

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalars.return_value.all.return_value = tracked_series
            else:
                result.scalar_one_or_none.return_value = None
            return result

        mock_db.execute = mock_execute

        recent_book = make_mock_book("book-1", "series-1", "1", datetime.now(UTC))

        with patch("app.services.pulllist.KomgaClient") as mock_komga_cls:
            mock_komga = AsyncMock()
            mock_komga.get_series_books = AsyncMock(return_value=[recent_book])
            mock_komga.get_book_read_url = MagicMock(return_value="http://localhost/read")
            mock_komga_cls.return_value.__aenter__.return_value = mock_komga

            with patch("app.services.pulllist.MylarClient") as mock_mylar_cls:
                mock_mylar = AsyncMock()
                mock_mylar.test_connection = AsyncMock(return_value=False)
                mock_mylar_cls.return_value.__aenter__.return_value = mock_mylar

                service = PullListService(mock_db)
                result = await service.generate_pulllist(create_readlist=False)

        assert result.readlist_id is None
        assert result.readlist_name is None


class TestGeneratePulllistErrorHandling:
    """Tests for error handling in generate_pulllist."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    async def test_komga_error_returns_failure(self, mock_db):
        """Komga API error should result in failed result."""
        tracked_series = [
            make_mock_tracked_series(1, "series-1", "Spider-Man"),
        ]

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalars.return_value.all.return_value = tracked_series
            return result

        mock_db.execute = mock_execute

        with patch("app.services.pulllist.KomgaClient") as mock_komga_cls:
            mock_komga = AsyncMock()
            mock_komga.get_series_books = AsyncMock(side_effect=Exception("Komga API error"))
            mock_komga_cls.return_value.__aenter__.return_value = mock_komga

            service = PullListService(mock_db)
            result = await service.generate_pulllist()

        assert result.success is False
        assert "Komga API error" in result.error
        assert result.items == []

    async def test_error_records_failed_run(self, mock_db):
        """Failed pulllist should record run with error status."""
        tracked_series = [
            make_mock_tracked_series(1, "series-1", "Spider-Man"),
        ]

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalars.return_value.all.return_value = tracked_series
            return result

        mock_db.execute = mock_execute

        with patch("app.services.pulllist.KomgaClient") as mock_komga_cls:
            mock_komga = AsyncMock()
            mock_komga.get_series_books = AsyncMock(side_effect=Exception("API error"))
            mock_komga_cls.return_value.__aenter__.return_value = mock_komga

            service = PullListService(mock_db)
            await service.generate_pulllist()

        # Should have committed the error state
        assert mock_db.commit.call_count >= 1
