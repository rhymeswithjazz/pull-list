"""Komga API client."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

from app.config import get_settings


@dataclass
class KomgaSeries:
    """A series from Komga."""

    id: str
    name: str
    books_count: int
    books_read_count: int
    books_unread_count: int
    library_id: str
    metadata: dict[str, Any]

    @property
    def publisher(self) -> str | None:
        return self.metadata.get("publisher")

    @property
    def is_complete(self) -> bool:
        return self.books_count > 0 and self.books_read_count == self.books_count


@dataclass
class KomgaBook:
    """A book from Komga."""

    id: str
    series_id: str
    name: str
    number: str
    sort_number: float
    size_bytes: int
    created_date: datetime
    last_modified_date: datetime
    file_hash: str
    url: str
    metadata: dict[str, Any]
    read_progress: dict[str, Any] | None
    pages_count: int = 0

    @property
    def is_read(self) -> bool:
        if not self.read_progress:
            return False
        return self.read_progress.get("completed", False)

    @property
    def pages_read(self) -> int:
        """Number of pages read (0 if not started)."""
        if not self.read_progress:
            return 0
        return self.read_progress.get("page", 0)

    @property
    def read_percentage(self) -> int:
        """Percentage of book read (0-100)."""
        if not self.read_progress or self.pages_count == 0:
            return 0
        if self.is_read:
            return 100
        return min(100, int((self.pages_read / self.pages_count) * 100))

    @property
    def title(self) -> str | None:
        return self.metadata.get("title")


class KomgaClient:
    """Client for interacting with the Komga API."""

    def __init__(
        self,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        api_key: str | None = None,
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.komga_url).rstrip("/")
        self.username = username or settings.komga_username
        self.password = password or settings.komga_password
        self.api_key = api_key or settings.komga_api_key
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "KomgaClient":
        headers = {}
        auth = None

        if self.api_key:
            headers["X-API-Key"] = self.api_key
        elif self.username and self.password:
            auth = httpx.BasicAuth(self.username, self.password)

        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers=headers,
            auth=auth,
        )
        return self

    async def __aexit__(self, *args) -> None:
        if self._client:
            await self._client.aclose()

    async def _get(self, path: str, **params) -> Any:
        """Make GET request and return JSON response."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        url = f"{self.base_url}{path}"
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def _post(self, path: str, json: dict[str, Any] | None = None) -> Any:
        """Make POST request and return JSON response."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        url = f"{self.base_url}{path}"
        response = await self._client.post(url, json=json)

        if not response.is_success:
            # Capture error details from response body
            error_body = response.text
            import logging

            logging.getLogger(__name__).error(
                f"POST {path} failed with {response.status_code}: {error_body}"
            )
            response.raise_for_status()

        if response.content:
            return response.json()
        return None

    async def test_connection(self) -> bool:
        """Test connection to Komga."""
        try:
            # Use libraries endpoint as a simple connectivity check
            await self._get("/api/v1/libraries")
            return True
        except Exception:
            return False

    async def get_series(
        self,
        page: int = 0,
        size: int = 500,
        search: str | None = None,
        library_id: str | None = None,
    ) -> list[KomgaSeries]:
        """Get all series from Komga."""
        params: dict[str, Any] = {"page": page, "size": size}
        if search:
            params["search"] = search
        if library_id:
            params["library_id"] = library_id

        data = await self._get("/api/v1/series", **params)
        content = data.get("content", [])

        return [self._parse_series(s) for s in content]

    async def get_series_by_id(self, series_id: str) -> KomgaSeries:
        """Get a specific series by ID."""
        data = await self._get(f"/api/v1/series/{series_id}")
        return self._parse_series(data)

    async def get_book_by_id(self, book_id: str) -> KomgaBook:
        """Get a specific book by ID with current read progress."""
        data = await self._get(f"/api/v1/books/{book_id}")
        return self._parse_book(data)

    async def get_books_by_ids(self, book_ids: list[str]) -> dict[str, KomgaBook]:
        """Get multiple books by IDs. Returns a dict mapping book_id to KomgaBook."""
        import asyncio

        async def fetch_book(book_id: str) -> tuple[str, KomgaBook | None]:
            try:
                book = await self.get_book_by_id(book_id)
                return (book_id, book)
            except Exception:
                return (book_id, None)

        results = await asyncio.gather(*[fetch_book(bid) for bid in book_ids])
        return {bid: book for bid, book in results if book is not None}

    async def get_series_books(
        self,
        series_id: str,
        page: int = 0,
        size: int = 500,
    ) -> list[KomgaBook]:
        """Get all books in a series."""
        data = await self._get(
            f"/api/v1/series/{series_id}/books",
            page=page,
            size=size,
        )
        content = data.get("content", [])
        return [self._parse_book(b) for b in content]

    async def get_latest_books(
        self,
        page: int = 0,
        size: int = 50,
    ) -> list[KomgaBook]:
        """Get recently added/updated books."""
        data = await self._get("/api/v1/books/latest", page=page, size=size)
        content = data.get("content", [])
        return [self._parse_book(b) for b in content]

    async def get_book_thumbnail_url(self, book_id: str) -> str:
        """Get the URL for a book's thumbnail."""
        return f"{self.base_url}/api/v1/books/{book_id}/thumbnail"

    async def get_series_thumbnail_url(self, series_id: str) -> str:
        """Get the URL for a series thumbnail."""
        return f"{self.base_url}/api/v1/series/{series_id}/thumbnail"

    def get_book_read_url(self, book_id: str) -> str:
        """Get the URL to read a book in Komga web UI."""
        return f"{self.base_url}/book/{book_id}/read"

    async def create_readlist(
        self,
        name: str,
        book_ids: list[str],
        ordered: bool = True,
    ) -> dict[str, Any]:
        """Create a new reading list."""
        payload = {
            "name": name,
            "bookIds": book_ids,
            "ordered": ordered,
        }
        result = await self._post("/api/v1/readlists", json=payload)
        # Log for debugging
        import logging

        logging.getLogger(__name__).info(f"Readlist creation response: {result}")
        return result

    async def get_readlists(
        self,
        page: int = 0,
        size: int = 100,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get all reading lists."""
        params: dict[str, Any] = {"page": page, "size": size}
        if search:
            params["search"] = search

        data = await self._get("/api/v1/readlists", **params)
        return data.get("content", [])

    async def find_readlist_by_name(self, name: str) -> dict[str, Any] | None:
        """Find a readlist by exact name."""
        import logging

        logger = logging.getLogger(__name__)

        # Get all readlists and search manually (search param may not work as expected)
        readlists = await self.get_readlists(size=500)
        logger.info(f"Looking for readlist '{name}' among {len(readlists)} readlists")

        for rl in readlists:
            logger.debug(f"Checking readlist: {rl.get('name')}")
            if rl.get("name") == name:
                logger.info(f"Found matching readlist: {rl.get('id')}")
                return rl

        logger.info(f"No readlist found with name '{name}'")
        return None

    async def delete_readlist(self, readlist_id: str) -> None:
        """Delete a reading list."""
        import logging

        logger = logging.getLogger(__name__)

        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        url = f"{self.base_url}/api/v1/readlists/{readlist_id}"
        logger.info(f"Deleting readlist: DELETE {url}")
        response = await self._client.delete(url)

        if not response.is_success:
            logger.error(f"Delete failed with {response.status_code}: {response.text}")

        response.raise_for_status()
        logger.info(f"Successfully deleted readlist {readlist_id}")

    def _parse_series(self, data: dict[str, Any]) -> KomgaSeries:
        """Parse series data from API response."""
        return KomgaSeries(
            id=data["id"],
            name=data["name"],
            books_count=data.get("booksCount", 0),
            books_read_count=data.get("booksReadCount", 0),
            books_unread_count=data.get("booksUnreadCount", 0),
            library_id=data.get("libraryId", ""),
            metadata=data.get("metadata", {}),
        )

    def _parse_book(self, data: dict[str, Any]) -> KomgaBook:
        """Parse book data from API response."""
        # Get pages count from media field
        media = data.get("media", {})
        pages_count = media.get("pagesCount", 0) if media else 0

        return KomgaBook(
            id=data["id"],
            series_id=data.get("seriesId", ""),
            name=data["name"],
            number=data.get("number", ""),
            sort_number=data.get("sortNumber", 0.0),
            size_bytes=data.get("sizeBytes", 0),
            created_date=datetime.fromisoformat(
                data.get("created", datetime.now().isoformat()).replace("Z", "+00:00")
            ),
            last_modified_date=datetime.fromisoformat(
                data.get("lastModified", datetime.now().isoformat()).replace("Z", "+00:00")
            ),
            file_hash=data.get("fileHash", ""),
            url=data.get("url", ""),
            metadata=data.get("metadata", {}),
            read_progress=data.get("readProgress"),
            pages_count=pages_count,
        )
