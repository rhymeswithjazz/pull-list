#!/usr/bin/env python3
"""
One-time fix script to populate is_one_off values in production database.

This script should be run when the is_one_off column exists but hasn't been populated.
It's safe to run multiple times - it will update all records to the correct values.
"""

import asyncio

from sqlalchemy import text

from app.database import async_session, init_db


async def fix_is_one_off():
    """Populate is_one_off values based on tracked_series_id."""
    print("Starting is_one_off fix for production database...")

    await init_db()

    async with async_session() as session:
        # Update all records based on whether they have a tracked_series_id
        result = await session.execute(
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
        updated_count = result.rowcount
        await session.commit()

        print(f"✓ Updated {updated_count} records")

        # Show statistics
        result = await session.execute(
            text("SELECT COUNT(*) FROM weekly_books WHERE is_one_off = 1")
        )
        one_offs = result.scalar()

        result = await session.execute(
            text("SELECT COUNT(*) FROM weekly_books WHERE is_one_off = 0")
        )
        tracked = result.scalar()

        print("\nResults:")
        print(f"  One-off books: {one_offs}")
        print(f"  Tracked series books: {tracked}")
        print("\n✓ Fix complete!")


if __name__ == "__main__":
    asyncio.run(fix_is_one_off())
