"""SQLAlchemy models for the pull-list application."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class TrackedSeries(Base):
    """A comic series that the user actively reads weekly."""

    __tablename__ = "tracked_series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Display info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Komga identifiers
    komga_series_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    # Mylar identifiers (optional - for upcoming issue tracking)
    mylar_comic_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Tracking
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<TrackedSeries {self.name} (komga={self.komga_series_id})>"


class PullListRun(Base):
    """Record of a pull-list generation run."""

    __tablename__ = "pulllist_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Run info
    run_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "manual" or "scheduled"
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # "running", "success", "failed"

    # Results
    books_found: Mapped[int] = mapped_column(Integer, default=0)
    readlist_created: Mapped[bool] = mapped_column(Boolean, default=False)
    readlist_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    readlist_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<PullListRun {self.id} ({self.status})>"


class WeeklyBook(Base):
    """A book included in a weekly pull-list."""

    __tablename__ = "weekly_books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Week identification (ISO week format: 2024-W48)
    week_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    # Book info from Komga
    komga_book_id: Mapped[str] = mapped_column(String(255), nullable=False)
    komga_series_id: Mapped[str] = mapped_column(String(255), nullable=False)
    series_name: Mapped[str] = mapped_column(String(255), nullable=False)
    book_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    book_title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)

    # Mylar info (if matched)
    mylar_issue_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    release_date: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<WeeklyBook {self.series_name} #{self.book_number}>"
