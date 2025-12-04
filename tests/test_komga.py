"""Tests for Komga service - data classes and parsing."""

from datetime import UTC, datetime

from app.services.komga import KomgaBook, KomgaClient, KomgaSeries


class TestKomgaBookProperties:
    """Tests for KomgaBook computed properties."""

    def _make_book(
        self,
        read_progress: dict | None = None,
        pages_count: int = 24,
    ) -> KomgaBook:
        """Helper to create a KomgaBook with specified properties."""
        return KomgaBook(
            id="book-123",
            series_id="series-456",
            name="Test Book.cbz",
            number="1",
            sort_number=1.0,
            size_bytes=50000000,
            created_date=datetime(2024, 11, 27, tzinfo=UTC),
            last_modified_date=datetime(2024, 11, 27, tzinfo=UTC),
            file_hash="abc123",
            url="/api/v1/books/book-123/file",
            metadata={"title": "Test Book #1"},
            read_progress=read_progress,
            pages_count=pages_count,
        )

    # is_read property tests
    def test_is_read_no_progress(self):
        """Book with no read_progress should not be read."""
        book = self._make_book(read_progress=None)
        assert book.is_read is False

    def test_is_read_empty_progress(self):
        """Book with empty read_progress should not be read."""
        book = self._make_book(read_progress={})
        assert book.is_read is False

    def test_is_read_not_completed(self):
        """Book with completed=False should not be read."""
        book = self._make_book(read_progress={"completed": False, "page": 10})
        assert book.is_read is False

    def test_is_read_completed(self):
        """Book with completed=True should be read."""
        book = self._make_book(read_progress={"completed": True, "page": 24})
        assert book.is_read is True

    # pages_read property tests
    def test_pages_read_no_progress(self):
        """Book with no read_progress should have 0 pages read."""
        book = self._make_book(read_progress=None)
        assert book.pages_read == 0

    def test_pages_read_empty_progress(self):
        """Book with empty read_progress should have 0 pages read."""
        book = self._make_book(read_progress={})
        assert book.pages_read == 0

    def test_pages_read_with_page(self):
        """Book should return page count from read_progress."""
        book = self._make_book(read_progress={"page": 15, "completed": False})
        assert book.pages_read == 15

    # read_percentage property tests - CRITICAL
    def test_read_percentage_no_progress(self):
        """Book with no progress should be 0%."""
        book = self._make_book(read_progress=None, pages_count=24)
        assert book.read_percentage == 0

    def test_read_percentage_zero_pages_count(self):
        """Book with 0 pages should return 0% (not divide by zero)."""
        book = self._make_book(read_progress={"page": 0}, pages_count=0)
        assert book.read_percentage == 0

    def test_read_percentage_completed(self):
        """Completed book should be 100%."""
        book = self._make_book(read_progress={"completed": True, "page": 24}, pages_count=24)
        assert book.read_percentage == 100

    def test_read_percentage_partial(self):
        """Partially read book should show correct percentage."""
        book = self._make_book(read_progress={"completed": False, "page": 12}, pages_count=24)
        assert book.read_percentage == 50

    def test_read_percentage_almost_done(self):
        """Book almost done but not completed should show <100%."""
        book = self._make_book(read_progress={"completed": False, "page": 23}, pages_count=24)
        # 23/24 = 95.8%, should round to 95
        assert book.read_percentage == 95

    def test_read_percentage_capped_at_100(self):
        """Percentage should never exceed 100."""
        # Edge case: page count exceeds pages_count (data inconsistency)
        book = self._make_book(read_progress={"completed": False, "page": 30}, pages_count=24)
        assert book.read_percentage == 100

    def test_read_percentage_one_page(self):
        """Book with one page read should show correct small percentage."""
        book = self._make_book(read_progress={"completed": False, "page": 1}, pages_count=100)
        assert book.read_percentage == 1

    # title property tests
    def test_title_from_metadata(self):
        """Title should come from metadata."""
        book = self._make_book()
        assert book.title == "Test Book #1"

    def test_title_missing_from_metadata(self):
        """Title should be None if not in metadata."""
        book = KomgaBook(
            id="book-123",
            series_id="series-456",
            name="Test.cbz",
            number="1",
            sort_number=1.0,
            size_bytes=50000000,
            created_date=datetime.now(UTC),
            last_modified_date=datetime.now(UTC),
            file_hash="abc",
            url="/api/v1/books/book-123/file",
            metadata={},  # No title
            read_progress=None,
            pages_count=24,
        )
        assert book.title is None


class TestKomgaSeriesProperties:
    """Tests for KomgaSeries computed properties."""

    def _make_series(
        self,
        books_count: int = 10,
        books_read_count: int = 0,
        metadata: dict | None = None,
    ) -> KomgaSeries:
        """Helper to create a KomgaSeries with specified properties."""
        return KomgaSeries(
            id="series-456",
            name="Test Series",
            books_count=books_count,
            books_read_count=books_read_count,
            books_unread_count=books_count - books_read_count,
            library_id="lib-001",
            metadata=metadata or {},
        )

    # is_complete property tests
    def test_is_complete_all_read(self):
        """Series with all books read should be complete."""
        series = self._make_series(books_count=10, books_read_count=10)
        assert series.is_complete is True

    def test_is_complete_some_unread(self):
        """Series with unread books should not be complete."""
        series = self._make_series(books_count=10, books_read_count=5)
        assert series.is_complete is False

    def test_is_complete_none_read(self):
        """Series with no books read should not be complete."""
        series = self._make_series(books_count=10, books_read_count=0)
        assert series.is_complete is False

    def test_is_complete_empty_series(self):
        """Empty series (0 books) should not be complete."""
        series = self._make_series(books_count=0, books_read_count=0)
        assert series.is_complete is False

    # publisher property tests
    def test_publisher_from_metadata(self):
        """Publisher should come from metadata."""
        series = self._make_series(metadata={"publisher": "Marvel"})
        assert series.publisher == "Marvel"

    def test_publisher_missing(self):
        """Publisher should be None if not in metadata."""
        series = self._make_series(metadata={})
        assert series.publisher is None


class TestKomgaClientParsing:
    """Tests for KomgaClient parsing methods."""

    def test_parse_series_full_data(self, sample_series_data):
        """_parse_series should correctly parse complete API response."""
        client = KomgaClient()
        series = client._parse_series(sample_series_data)

        assert series.id == "series-456"
        assert series.name == "Amazing Spider-Man"
        assert series.books_count == 10
        assert series.books_read_count == 5
        assert series.books_unread_count == 5
        assert series.library_id == "lib-001"
        assert series.publisher == "Marvel"

    def test_parse_series_minimal_data(self):
        """_parse_series should handle minimal data with defaults."""
        client = KomgaClient()
        minimal_data = {"id": "s-1", "name": "Test Series"}
        series = client._parse_series(minimal_data)

        assert series.id == "s-1"
        assert series.name == "Test Series"
        assert series.books_count == 0
        assert series.books_read_count == 0
        assert series.books_unread_count == 0
        assert series.library_id == ""
        assert series.metadata == {}

    def test_parse_book_full_data(self, sample_book_data):
        """_parse_book should correctly parse complete API response."""
        client = KomgaClient()
        book = client._parse_book(sample_book_data)

        assert book.id == "book-123"
        assert book.series_id == "series-456"
        assert book.name == "Amazing Spider-Man 001.cbz"
        assert book.number == "1"
        assert book.sort_number == 1.0
        assert book.pages_count == 24
        assert book.title == "Amazing Spider-Man #1"

    def test_parse_book_datetime_with_z_suffix(self, sample_book_data):
        """_parse_book should handle Z timezone suffix in dates."""
        client = KomgaClient()
        book = client._parse_book(sample_book_data)

        assert book.created_date.year == 2024
        assert book.created_date.month == 11
        assert book.created_date.day == 27
        assert book.created_date.tzinfo is not None

    def test_parse_book_minimal_data(self):
        """_parse_book should handle minimal data with defaults."""
        client = KomgaClient()
        minimal_data = {"id": "b-1", "name": "Test.cbz"}
        book = client._parse_book(minimal_data)

        assert book.id == "b-1"
        assert book.name == "Test.cbz"
        assert book.series_id == ""
        assert book.number == ""
        assert book.pages_count == 0

    def test_parse_book_no_media_field(self):
        """_parse_book should handle missing media field."""
        client = KomgaClient()
        data = {
            "id": "b-1",
            "name": "Test.cbz",
            "created": "2024-11-27T10:00:00Z",
            "lastModified": "2024-11-27T10:00:00Z",
        }
        book = client._parse_book(data)

        assert book.pages_count == 0

    def test_parse_book_null_read_progress(self, sample_book_data):
        """_parse_book should handle null read_progress."""
        client = KomgaClient()
        sample_book_data["readProgress"] = None
        book = client._parse_book(sample_book_data)

        assert book.read_progress is None
        assert book.is_read is False
        assert book.pages_read == 0
        assert book.read_percentage == 0

    def test_parse_book_with_read_progress(self, sample_book_data):
        """_parse_book should handle read_progress correctly."""
        client = KomgaClient()
        sample_book_data["readProgress"] = {"page": 12, "completed": False}
        book = client._parse_book(sample_book_data)

        assert book.read_progress == {"page": 12, "completed": False}
        assert book.is_read is False
        assert book.pages_read == 12
        assert book.read_percentage == 50


class TestKomgaClientUrlMethods:
    """Tests for KomgaClient URL construction methods."""

    def test_get_book_read_url(self):
        """get_book_read_url should construct correct URL."""
        client = KomgaClient(base_url="http://localhost:25600")
        url = client.get_book_read_url("book-123")
        assert url == "http://localhost:25600/book/book-123/read"

    def test_get_book_read_url_strips_trailing_slash(self):
        """URL construction should handle base_url with trailing slash."""
        client = KomgaClient(base_url="http://localhost:25600/")
        url = client.get_book_read_url("book-123")
        assert url == "http://localhost:25600/book/book-123/read"
