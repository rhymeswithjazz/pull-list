#!/usr/bin/env python3
"""
Migration script to add and populate the is_one_off field in existing databases.

This script should be run once after updating to the version that includes the is_one_off field.
It will:
1. Add the is_one_off column if it doesn't exist (SQLite will add it automatically)
2. Set is_one_off=False for all books that have a tracked_series_id
3. Set is_one_off=True for all books that have tracked_series_id=NULL
"""

import asyncio

from sqlalchemy import text

from app.database import async_session_maker, init_db


async def migrate():
    """Run the migration."""
    print("Starting migration...")

    # Initialize database (creates tables if needed, adds new columns)
    await init_db()
    print("Database schema updated")

    # Update existing records
    async with async_session_maker() as session:
        # Set is_one_off=True for books with NULL tracked_series_id
        result = await session.execute(
            text(
                """
                UPDATE weekly_books
                SET is_one_off = TRUE
                WHERE tracked_series_id IS NULL
                """
            )
        )
        one_offs_updated = result.rowcount
        print(f"Marked {one_offs_updated} books as one-offs")

        # Set is_one_off=False for books with a tracked_series_id
        result = await session.execute(
            text(
                """
                UPDATE weekly_books
                SET is_one_off = FALSE
                WHERE tracked_series_id IS NOT NULL
                """
            )
        )
        tracked_updated = result.rowcount
        print(f"Marked {tracked_updated} books as tracked series")

        await session.commit()

    print("Migration complete!")


if __name__ == "__main__":
    asyncio.run(migrate())
