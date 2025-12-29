"""Database migrations for schema changes."""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def run_migrations(db: AsyncSession) -> None:
    """Run all pending database migrations."""
    await add_tracked_series_id_column(db)


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
