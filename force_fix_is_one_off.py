#!/usr/bin/env python3
"""
Force fix all is_one_off values regardless of current state.
Run this on production to ensure all values are correct.
"""

import asyncio

from sqlalchemy import text

from app.database import async_session, init_db


async def force_fix():
    """Force update all is_one_off values based on tracked_series_id."""
    print("Force fixing all is_one_off values...")

    await init_db()

    async with async_session() as session:
        # Show current state BEFORE fix
        print("\nBEFORE fix:")
        result = await session.execute(
            text(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN is_one_off = 1 THEN 1 ELSE 0 END) as marked_one_off,
                    SUM(CASE WHEN is_one_off = 0 THEN 1 ELSE 0 END) as marked_tracked,
                    SUM(CASE WHEN tracked_series_id IS NOT NULL THEN 1 ELSE 0 END) as has_tracked_id,
                    SUM(CASE WHEN tracked_series_id IS NULL THEN 1 ELSE 0 END) as no_tracked_id
                FROM weekly_books
                """
            )
        )
        row = result.fetchone()
        print(f"  Total books: {row[0]}")
        print(f"  Marked as one-off (is_one_off=1): {row[1]}")
        print(f"  Marked as tracked (is_one_off=0): {row[2]}")
        print(f"  Has tracked_series_id: {row[3]}")
        print(f"  No tracked_series_id: {row[4]}")

        # Force update ALL records
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

        print(f"\n✓ Updated {updated_count} records")

        # Show state AFTER fix
        print("\nAFTER fix:")
        result = await session.execute(
            text(
                """
                SELECT
                    SUM(CASE WHEN is_one_off = 1 THEN 1 ELSE 0 END) as one_offs,
                    SUM(CASE WHEN is_one_off = 0 THEN 1 ELSE 0 END) as tracked
                FROM weekly_books
                """
            )
        )
        row = result.fetchone()
        print(f"  One-off books: {row[0]}")
        print(f"  Tracked series books: {row[1]}")
        print("\n✓ Fix complete!")


if __name__ == "__main__":
    asyncio.run(force_fix())
