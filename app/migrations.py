"""Database migrations for schema changes."""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def run_migrations(db: AsyncSession) -> None:
    """Run all pending database migrations."""
    await add_tracked_series_id_column(db)
    await add_is_one_off_column(db)


async def add_tracked_series_id_column(db: AsyncSession) -> None:
    """Add tracked_series_id column to weekly_books table if it doesn't exist."""
    try:
        # Check if column exists
        result = await db.execute(text("PRAGMA table_info(weekly_books)"))
        columns = result.fetchall()
        column_names = [col[1] for col in columns]

        if "tracked_series_id" not in column_names:
            logger.info("Adding tracked_series_id column to weekly_books table...")
            await db.execute(
                text(
                    """
                    ALTER TABLE weekly_books
                    ADD COLUMN tracked_series_id INTEGER
                    REFERENCES tracked_series(id) ON DELETE SET NULL
                    """
                )
            )
            await db.commit()
            logger.info("Successfully added tracked_series_id column")
        else:
            logger.info("tracked_series_id column already exists, skipping migration")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        await db.rollback()
        raise


async def add_is_one_off_column(db: AsyncSession) -> None:
    """Add is_one_off column to weekly_books table and populate it."""
    try:
        # Check if column exists
        result = await db.execute(text("PRAGMA table_info(weekly_books)"))
        columns = result.fetchall()
        column_names = [col[1] for col in columns]

        column_exists = "is_one_off" in column_names

        if not column_exists:
            logger.info("Adding is_one_off column to weekly_books table...")
            await db.execute(
                text(
                    """
                    ALTER TABLE weekly_books
                    ADD COLUMN is_one_off BOOLEAN NOT NULL DEFAULT 0
                    """
                )
            )
            logger.info("Successfully added is_one_off column")
        else:
            logger.info("is_one_off column already exists")

        # One-time fix: Set all books to is_one_off = False
        # Check if any books have is_one_off = True (need fixing)
        result = await db.execute(text("SELECT COUNT(*) FROM weekly_books WHERE is_one_off = 1"))
        needs_fix = result.scalar() > 0

        if needs_fix or not column_exists:
            logger.info("Setting all books to is_one_off = False...")
            result = await db.execute(text("UPDATE weekly_books SET is_one_off = 0"))
            updated_count = result.rowcount
            await db.commit()
            logger.info(f"Set {updated_count} books to is_one_off = False")
        else:
            logger.info("All books already have is_one_off = False, skipping")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        await db.rollback()
        raise
