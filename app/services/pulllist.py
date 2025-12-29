"""Pull-list generation service."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PullListRun, TrackedSeries, WeeklyBook
from app.services.komga import KomgaClient
from app.services.mylar import MylarClient


@dataclass
class PullListItem:
    """A single item in the weekly pull-list."""

    # Series info
    series_name: str
    komga_series_id: str
    mylar_comic_id: str | None

    # Book info (from Komga, if downloaded)
    komga_book_id: str | None
    book_number: str
    book_title: str | None

    # Status
    is_downloaded: bool
    is_read: bool
    release_date: str | None

    # URLs
    thumbnail_url: str | None
    read_url: str | None

    # Mylar info (for upcoming tracking)
    mylar_issue_id: str | None = None

    # Read progress (percentage 0-100)
    read_percentage: int = 0


@dataclass
class PullListResult:
    """Result of a pull-list generation run."""

    success: bool
    items: list[PullListItem]
    readlist_id: str | None
    readlist_name: str | None
    week_id: str
    error: str | None = None


def get_week_id_for_date(dt: datetime) -> str:
    """Get the comic week ID for a date.

    Comic weeks run Wednesday-Tuesday, so we shift the date back by 2 days
    to align with ISO weeks (Monday-Sunday). This way Wednesday-Tuesday
    maps to the same week ID.
    """
    # Remove timezone info if present for consistent calculation
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)

    # Shift date so that Wednesday becomes the "start" of the week
    # Wednesday is weekday 2, we want it to act like Monday (weekday 0)
    # So we add 5 days (or subtract 2 from the weekday calculation)
    adjusted = dt - timedelta(days=2)
    return adjusted.strftime("%G-W%V")


def get_current_week_id() -> str:
    """Get the comic week ID for the current week."""
    return get_week_id_for_date(datetime.now())


def get_week_start_date(week_id: str | None = None) -> datetime:
    """Get the start date (Wednesday) of the specified comic week."""
    if week_id:
        year, week = week_id.split("-W")
        # Get the Monday of the ISO week, then add 2 days to get Wednesday
        monday = datetime.strptime(f"{year}-W{week}-1", "%G-W%V-%u")
        return monday + timedelta(days=2)
    # Default to current comic week's Wednesday
    now = datetime.now()
    # Find this week's Wednesday
    days_since_wednesday = (now.weekday() - 2) % 7
    return now - timedelta(days=days_since_wednesday)


def get_previous_week_id(week_id: str) -> str:
    """Get the ISO week ID for the previous week."""
    week_start = get_week_start_date(week_id)
    prev_week = week_start - timedelta(days=7)
    return prev_week.strftime("%G-W%V")


def get_next_week_id(week_id: str) -> str:
    """Get the ISO week ID for the next week."""
    week_start = get_week_start_date(week_id)
    next_week = week_start + timedelta(days=7)
    return next_week.strftime("%G-W%V")


def format_week_display(week_id: str) -> str:
    """Format week ID for display (e.g., 'Nov 26 - Dec 2, 2024').

    Shows Wednesday-Tuesday range for comic weeks.
    """
    week_start = get_week_start_date(week_id)  # Wednesday
    week_end = week_start + timedelta(days=6)  # Tuesday
    if week_start.month == week_end.month:
        return f"{week_start.strftime('%b %d')} - {week_end.strftime('%d, %Y')}"
    elif week_start.year == week_end.year:
        return f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}"
    else:
        return f"{week_start.strftime('%b %d, %Y')} - {week_end.strftime('%b %d, %Y')}"


class PullListService:
    """Service for generating weekly pull-lists."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tracked_series(self, active_only: bool = True) -> list[TrackedSeries]:
        """Get all tracked series from the database."""
        query = select(TrackedSeries)
        if active_only:
            query = query.where(TrackedSeries.is_active.is_(True))
        query = query.order_by(TrackedSeries.name)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def add_tracked_series(
        self,
        name: str,
        komga_series_id: str,
        mylar_comic_id: str | None = None,
        publisher: str | None = None,
    ) -> TrackedSeries:
        """Add a new series to track."""
        series = TrackedSeries(
            name=name,
            komga_series_id=komga_series_id,
            mylar_comic_id=mylar_comic_id,
            publisher=publisher,
        )
        self.db.add(series)
        await self.db.commit()
        await self.db.refresh(series)
        return series

    async def remove_tracked_series(self, series_id: int) -> bool:
        """Remove a series from tracking."""
        query = select(TrackedSeries).where(TrackedSeries.id == series_id)
        result = await self.db.execute(query)
        series = result.scalar_one_or_none()

        if series:
            await self.db.delete(series)
            await self.db.commit()
            return True
        return False

    async def toggle_tracked_series(self, series_id: int) -> TrackedSeries | None:
        """Toggle the active status of a tracked series."""
        query = select(TrackedSeries).where(TrackedSeries.id == series_id)
        result = await self.db.execute(query)
        series = result.scalar_one_or_none()

        if series:
            series.is_active = not series.is_active
            await self.db.commit()
            await self.db.refresh(series)
            return series
        return None

    async def generate_pulllist(
        self,
        run_type: str = "manual",
        days_back: int = 7,
        create_readlist: bool = True,
    ) -> PullListResult:
        """Generate the weekly pull-list.

        Args:
            run_type: "manual" or "scheduled"
            days_back: Number of days to look back for new books
            create_readlist: Whether to create a Komga readlist
        """
        week_id = get_current_week_id()
        cutoff_date = datetime.now(UTC) - timedelta(days=days_back)

        # Create run record
        run = PullListRun(
            run_type=run_type,
            status="running",
        )
        self.db.add(run)
        await self.db.commit()

        try:
            # Get tracked series
            tracked = await self.get_tracked_series(active_only=True)
            if not tracked:
                run.status = "success"
                run.completed_at = datetime.now()
                run.books_found = 0
                await self.db.commit()
                return PullListResult(
                    success=True,
                    items=[],
                    readlist_id=None,
                    readlist_name=None,
                    week_id=week_id,
                )

            # Build lookup for tracked series (by Mylar ID for upcoming matching)
            tracked_by_mylar_id = {s.mylar_comic_id: s for s in tracked if s.mylar_comic_id}

            # Fetch data from both services
            pull_list_items: list[PullListItem] = []
            komga_book_ids: list[str] = []

            # Clear only tracked series books, preserve one-offs
            await self.db.execute(
                delete(WeeklyBook).where(
                    WeeklyBook.week_id == week_id,
                    WeeklyBook.tracked_series_id.isnot(None),
                )
            )
            await self.db.commit()

            async with KomgaClient() as komga:
                # Get new books from tracked series
                for series in tracked:
                    books = await komga.get_series_books(series.komga_series_id)

                    # Filter to recently added books
                    new_books = [b for b in books if b.created_date >= cutoff_date]

                    for book in new_books:
                        # Use proxy URLs for thumbnails
                        thumbnail_url = f"/api/proxy/book/{book.id}/thumbnail"
                        read_url = komga.get_book_read_url(book.id)

                        item = PullListItem(
                            series_name=series.name,
                            komga_series_id=series.komga_series_id,
                            mylar_comic_id=series.mylar_comic_id,
                            komga_book_id=book.id,
                            book_number=book.number,
                            book_title=book.title,
                            is_downloaded=True,
                            is_read=book.is_read,
                            read_percentage=book.read_percentage,
                            release_date=None,
                            thumbnail_url=thumbnail_url,
                            read_url=read_url,
                        )
                        pull_list_items.append(item)

                        # Determine week based on book's created date
                        book_week_id = get_week_id_for_date(book.created_date)

                        # Only add to readlist if book belongs to current week
                        if book_week_id == week_id:
                            komga_book_ids.append(book.id)

                        # Save to weekly_books table (check for existing first)
                        existing = await self.db.execute(
                            select(WeeklyBook).where(
                                WeeklyBook.week_id == book_week_id,
                                WeeklyBook.komga_book_id == book.id,
                            )
                        )
                        if not existing.scalar_one_or_none():
                            weekly_book = WeeklyBook(
                                week_id=book_week_id,
                                komga_book_id=book.id,
                                komga_series_id=series.komga_series_id,
                                series_name=series.name,
                                book_number=book.number,
                                book_title=book.title,
                                is_read=book.is_read,
                                tracked_series_id=series.id,
                            )
                            self.db.add(weekly_book)

                # Try to get upcoming from Mylar (optional)
                try:
                    async with MylarClient() as mylar:
                        if await mylar.test_connection():
                            upcoming = await mylar.get_upcoming(include_downloaded=False)

                            for issue in upcoming:
                                # Check if this is a tracked series
                                tracked_series = tracked_by_mylar_id.get(issue.comic_id)
                                if not tracked_series:
                                    continue

                                # Check if we already have this issue from Komga
                                already_have = any(
                                    item.komga_series_id == tracked_series.komga_series_id
                                    and item.book_number == issue.issue_number
                                    for item in pull_list_items
                                )

                                if not already_have:
                                    # Add as upcoming (not downloaded) - use proxy URL
                                    thumbnail_url = f"/api/proxy/series/{tracked_series.komga_series_id}/thumbnail"

                                    item = PullListItem(
                                        series_name=issue.comic_name,
                                        komga_series_id=tracked_series.komga_series_id,
                                        mylar_comic_id=issue.comic_id,
                                        komga_book_id=None,
                                        book_number=issue.issue_number,
                                        book_title=None,
                                        is_downloaded=False,
                                        is_read=False,
                                        release_date=issue.release_date,
                                        thumbnail_url=thumbnail_url,
                                        read_url=None,
                                        mylar_issue_id=issue.issue_id,
                                    )
                                    pull_list_items.append(item)
                except Exception:
                    # Mylar connection is optional
                    pass

                # Create Komga readlist if requested and we have books
                readlist_id = None
                readlist_name = None

                if create_readlist and komga_book_ids:
                    readlist_name = f"Pull List - {week_id}"
                    try:
                        import logging

                        logger = logging.getLogger(__name__)

                        # Check if readlist already exists and delete it
                        logger.info(f"Checking for existing readlist: {readlist_name}")
                        existing = await komga.find_readlist_by_name(readlist_name)
                        if existing:
                            logger.info(f"Deleting existing readlist: {existing['id']}")
                            await komga.delete_readlist(existing["id"])
                            logger.info("Existing readlist deleted")

                        # Create fresh readlist
                        logger.info(
                            f"Creating readlist with {len(komga_book_ids)} books: {komga_book_ids}"
                        )
                        result = await komga.create_readlist(
                            name=readlist_name,
                            book_ids=komga_book_ids,
                            ordered=True,
                        )
                        logger.info(f"Readlist creation result: {result}")
                        readlist_id = result.get("id") if result else None
                    except Exception as e:
                        import traceback

                        error_details = (
                            f"Readlist creation failed: {str(e)}\n{traceback.format_exc()}"
                        )
                        logging.getLogger(__name__).error(error_details)
                        run.error_message = error_details

            # Sort items by series name, then issue number
            pull_list_items.sort(key=lambda x: (x.series_name, x.book_number))

            # Update run record
            run.status = "success"
            run.completed_at = datetime.now()
            run.books_found = len(pull_list_items)
            run.readlist_created = readlist_id is not None
            run.readlist_id = readlist_id
            run.readlist_name = readlist_name
            await self.db.commit()

            return PullListResult(
                success=True,
                items=pull_list_items,
                readlist_id=readlist_id,
                readlist_name=readlist_name,
                week_id=week_id,
            )

        except Exception as e:
            run.status = "failed"
            run.completed_at = datetime.now()
            run.error_message = str(e)
            await self.db.commit()

            return PullListResult(
                success=False,
                items=[],
                readlist_id=None,
                readlist_name=None,
                week_id=week_id,
                error=str(e),
            )

    async def get_week_books(self, week_id: str | None = None) -> list[WeeklyBook]:
        """Get all books for a specific week from the database."""
        if week_id is None:
            week_id = get_current_week_id()
        query = (
            select(WeeklyBook)
            .where(WeeklyBook.week_id == week_id)
            .order_by(WeeklyBook.series_name, WeeklyBook.book_number)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_available_weeks(self) -> list[str]:
        """Get list of weeks that have books, ordered newest first."""
        from sqlalchemy import distinct

        query = select(distinct(WeeklyBook.week_id)).order_by(WeeklyBook.week_id.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def has_books_for_week(self, week_id: str) -> bool:
        """Check if there are any books for a specific week."""
        from sqlalchemy import func

        query = select(func.count()).where(WeeklyBook.week_id == week_id)
        result = await self.db.execute(query)
        count = result.scalar()
        return count > 0

    async def clear_week_books(self, week_id: str) -> int:
        """Clear all books for a specific week. Returns count of deleted books."""
        from sqlalchemy import delete, func

        # Count first
        count_query = select(func.count()).where(WeeklyBook.week_id == week_id)
        result = await self.db.execute(count_query)
        count = result.scalar()

        # Delete
        delete_query = delete(WeeklyBook).where(WeeklyBook.week_id == week_id)
        await self.db.execute(delete_query)
        await self.db.commit()

        return count

    async def get_recent_runs(self, limit: int = 10) -> list[PullListRun]:
        """Get recent pull-list runs."""
        query = select(PullListRun).order_by(PullListRun.started_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_readlist_for_week(self, week_id: str) -> PullListRun | None:
        """Get the most recent successful run with a readlist for a specific week."""
        query = (
            select(PullListRun)
            .where(
                PullListRun.status == "success",
                PullListRun.readlist_created.is_(True),
                PullListRun.readlist_name.contains(week_id),
            )
            .order_by(PullListRun.started_at.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_weekly_books_for_browsing(self, week_id: str, days_back: int = 7) -> list:
        """Get all books from Komga for the week (for one-off browsing)."""
        week_start = get_week_start_date(week_id)
        cutoff_date = week_start - timedelta(days=days_back)

        async with KomgaClient() as komga:
            all_books = await komga.get_latest_books(size=500)
            return [b for b in all_books if b.created_date >= cutoff_date]

    async def add_one_off_book(self, week_id: str, komga_book_id: str) -> WeeklyBook:
        """Add a one-off book to the weekly pull-list."""
        # Check if already exists
        existing = await self.db.execute(
            select(WeeklyBook).where(
                WeeklyBook.week_id == week_id,
                WeeklyBook.komga_book_id == komga_book_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Book already in pull-list")

        # Fetch from Komga and create entry
        async with KomgaClient() as komga:
            book = await komga.get_book_by_id(komga_book_id)
            series = await komga.get_series_by_id(book.series_id)

        weekly_book = WeeklyBook(
            week_id=week_id,
            komga_book_id=book.id,
            komga_series_id=book.series_id,
            series_name=series.name,
            book_number=book.number,
            book_title=book.title,
            is_read=book.is_read,
            tracked_series_id=None,  # NULL = one-off
        )

        self.db.add(weekly_book)
        await self.db.commit()
        await self.db.refresh(weekly_book)
        return weekly_book

    async def promote_one_off_to_tracked(self, week_id: str, komga_book_id: str) -> TrackedSeries:
        """Promote a one-off book to a tracked series."""
        # Get the one-off book
        result = await self.db.execute(
            select(WeeklyBook).where(
                WeeklyBook.week_id == week_id,
                WeeklyBook.komga_book_id == komga_book_id,
                WeeklyBook.tracked_series_id.is_(None),
            )
        )
        weekly_book = result.scalar_one_or_none()
        if not weekly_book:
            raise ValueError("Book not found or already tracked")

        # Check if series already tracked
        existing = await self.db.execute(
            select(TrackedSeries).where(
                TrackedSeries.komga_series_id == weekly_book.komga_series_id
            )
        )
        series = existing.scalar_one_or_none()

        if not series:
            # Create new tracked series
            async with KomgaClient() as komga:
                komga_series = await komga.get_series_by_id(weekly_book.komga_series_id)

            series = await self.add_tracked_series(
                name=komga_series.name,
                komga_series_id=komga_series.id,
                publisher=komga_series.publisher,
            )

        # Update book to link to tracked series
        weekly_book.tracked_series_id = series.id
        await self.db.commit()

        return series
