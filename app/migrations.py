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

        # Always check if values need to be populated (handles case where column
        # was added but values weren't populated, e.g., from a partial migration)
        result = await db.execute(
            text(
                """
                SELECT COUNT(*) FROM weekly_books
                WHERE (tracked_series_id IS NULL AND is_one_off = 0)
                   OR (tracked_series_id IS NOT NULL AND is_one_off = 1)
                """
            )
        )
        inconsistent_count = result.scalar()

        if inconsistent_count > 0 or not column_exists:
            logger.info(
                f"Populating is_one_off values ({inconsistent_count} inconsistent records found)..."
            )
            await db.execute(
                text(
                    """
                    UPDATE weekly_books
                    SET is_one_off = CASE
                        WHEN tracked_series_id IS NULL THEN 1
                        ELSE 0
                    END
                    """
                )
            )
            await db.commit()
            logger.info("Successfully populated is_one_off values")
        else:
            logger.info("is_one_off values are already correct, skipping population")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        await db.rollback()
        raise
