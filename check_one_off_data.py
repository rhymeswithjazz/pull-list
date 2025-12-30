#!/usr/bin/env python3
"""Check for any inconsistent is_one_off values in the database."""

import asyncio

from sqlalchemy import select

from app.database import async_session, init_db
from app.models import WeeklyBook


async def check_data():
    """Check for data inconsistencies."""
    await init_db()

    async with async_session() as session:
        # Get all WeeklyBook records
        result = await session.execute(select(WeeklyBook))
        books = result.scalars().all()

        print(f"Total WeeklyBook records: {len(books)}\n")

        # Check for inconsistencies
        inconsistent = []
        for book in books:
            # Expected: is_one_off=True when tracked_series_id is None
            # Expected: is_one_off=False when tracked_series_id is not None
            expected_is_one_off = book.tracked_series_id is None

            if book.is_one_off != expected_is_one_off:
                inconsistent.append(
                    {
                        "id": book.id,
                        "komga_book_id": book.komga_book_id,
                        "book_title": book.book_title,
                        "tracked_series_id": book.tracked_series_id,
                        "is_one_off": book.is_one_off,
                        "expected_is_one_off": expected_is_one_off,
                    }
                )

        if inconsistent:
            print(f"Found {len(inconsistent)} inconsistent records:\n")
            for record in inconsistent:
                print(f"ID: {record['id']}")
                print(f"  Title: {record['book_title']}")
                print(f"  Komga Book ID: {record['komga_book_id']}")
                print(f"  tracked_series_id: {record['tracked_series_id']}")
                print(f"  is_one_off (actual): {record['is_one_off']}")
                print(f"  is_one_off (expected): {record['expected_is_one_off']}")
                print()
        else:
            print("No inconsistencies found! All is_one_off values are correct.")

        # Also show stats
        one_offs = sum(1 for book in books if book.is_one_off)
        tracked = sum(1 for book in books if not book.is_one_off)
        print("\nStats:")
        print(f"  One-off books: {one_offs}")
        print(f"  Tracked series books: {tracked}")


if __name__ == "__main__":
    asyncio.run(check_data())
