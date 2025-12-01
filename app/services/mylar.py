"""Mylar3 API client."""

from dataclasses import dataclass
from typing import Any

import httpx

from app.config import get_settings


@dataclass
class MylarComic:
    """A comic series from Mylar."""

    comic_id: str
    name: str
    status: str
    publisher: str | None = None
    year: str | None = None


@dataclass
class MylarUpcomingIssue:
    """An upcoming issue from Mylar."""

    issue_id: str
    comic_id: str
    comic_name: str
    issue_number: str
    release_date: str
    status: str


class MylarClient:
    """Client for interacting with the Mylar3 API."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.mylar_url).rstrip("/")
        self.api_key = api_key or settings.mylar_api_key
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "MylarClient":
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *args) -> None:
        if self._client:
            await self._client.aclose()

    def _build_url(self, cmd: str, **params) -> str:
        """Build API URL with command and parameters."""
        url = f"{self.base_url}/api?apikey={self.api_key}&cmd={cmd}"
        for key, value in params.items():
            if value is not None:
                url += f"&{key}={value}"
        return url

    async def _request(self, cmd: str, **params) -> Any:
        """Make API request and return JSON response."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        url = self._build_url(cmd, **params)
        response = await self._client.get(url)
        response.raise_for_status()
        return response.json()

    async def test_connection(self) -> bool:
        """Test connection to Mylar."""
        try:
            result = await self._request("getVersion")
            return "current_version" in result or "version" in str(result).lower()
        except Exception:
            return False

    async def get_index(self) -> list[MylarComic]:
        """Get all comics in the library."""
        data = await self._request("getIndex")

        comics = []
        for item in data if isinstance(data, list) else []:
            comics.append(
                MylarComic(
                    comic_id=str(item.get("ComicID", "")),
                    name=item.get("ComicName", ""),
                    status=item.get("Status", ""),
                    publisher=item.get("ComicPublisher"),
                    year=item.get("ComicYear"),
                )
            )
        return comics

    async def get_upcoming(self, include_downloaded: bool = True) -> list[MylarUpcomingIssue]:
        """Get upcoming issues for the current week.

        Args:
            include_downloaded: If True, includes issues that have already been downloaded.
        """
        params = {}
        if include_downloaded:
            params["include_downloaded_issues"] = "Y"

        data = await self._request("getUpcoming", **params)

        issues = []
        for item in data if isinstance(data, list) else []:
            issues.append(
                MylarUpcomingIssue(
                    issue_id=str(item.get("IssueID", "")),
                    comic_id=str(item.get("ComicID", "")),
                    comic_name=item.get("ComicName", ""),
                    issue_number=str(item.get("IssueNumber", "")),
                    release_date=item.get("IssueDate", ""),
                    status=item.get("Status", ""),
                )
            )
        return issues

    async def get_comic(self, comic_id: str) -> dict[str, Any]:
        """Get details for a specific comic."""
        return await self._request("getComic", id=comic_id)

    async def get_wanted(self) -> list[dict[str, Any]]:
        """Get all wanted issues."""
        data = await self._request("getWanted")
        return data if isinstance(data, list) else []

    async def search_comic(self, name: str) -> list[dict[str, Any]]:
        """Search for a comic by name."""
        data = await self._request("findComic", name=name)
        return data if isinstance(data, list) else []
