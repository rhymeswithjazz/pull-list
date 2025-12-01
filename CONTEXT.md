# Pull-List - Project Context

## Project Overview

Pull-List is a comic book pull-list dashboard that integrates with self-hosted Mylar3 and Komga instances. It allows users to track specific comic series and generates weekly reading lists with a visual cover grid interface.

### Target Audience
- Comic book readers with self-hosted media servers
- Users of Mylar3 (comic download manager) and Komga (comic server/reader)

### Key Requirements
- Track a curated subset of series (not all downloaded comics)
- Weekly pull-list generation with visual cover grid
- Direct links to read in Komga
- Automated Komga reading list creation
- Manual trigger option alongside scheduled runs

## Tech Stack

- **Language**: Python 3.12
- **Framework**: FastAPI 0.115.x
- **Frontend**: HTMX 1.9.x + Jinja2 templates + Tailwind CSS (CDN)
- **Database**: SQLite with SQLAlchemy 2.x (async)
- **Scheduling**: APScheduler 3.10.x
- **HTTP Client**: httpx 0.28.x
- **Build Tools**: Docker
- **Deployment**: Docker container via Portainer

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Pull-List App                          │
├─────────────────────────────────────────────────────────────┤
│  FastAPI Application                                         │
│  ├── Routes (main.py)                                       │
│  │   ├── / (dashboard)                                      │
│  │   ├── /settings                                          │
│  │   └── /api/* (HTMX endpoints)                           │
│  ├── Services                                               │
│  │   ├── KomgaClient - Komga API integration               │
│  │   ├── MylarClient - Mylar3 API integration              │
│  │   └── PullListService - Core business logic             │
│  ├── Models (SQLAlchemy)                                    │
│  │   ├── TrackedSeries                                      │
│  │   ├── PullListRun                                        │
│  │   └── WeeklyBook                                         │
│  └── Scheduler (APScheduler)                                │
│       └── Weekly cron job                                   │
├─────────────────────────────────────────────────────────────┤
│  External Services                                           │
│  ├── Komga API (required)                                   │
│  │   ├── GET /api/v1/series - List/search series           │
│  │   ├── GET /api/v1/series/{id}/books - Get books         │
│  │   └── POST /api/v1/readlists - Create reading list      │
│  └── Mylar3 API (optional)                                  │
│       └── getUpcoming - Get weekly releases                 │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
pull-list/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, routes
│   ├── config.py            # Settings (env vars)
│   ├── models.py            # SQLAlchemy models
│   ├── database.py          # DB connection
│   ├── scheduler.py         # APScheduler setup
│   ├── services/
│   │   ├── __init__.py
│   │   ├── mylar.py         # Mylar API client
│   │   ├── komga.py         # Komga API client
│   │   └── pulllist.py      # Core pull-list logic
│   └── templates/
│       ├── base.html
│       ├── dashboard.html
│       ├── settings.html
│       └── partials/
│           ├── pull_list_grid.html
│           ├── tracked_series_list.html
│           ├── series_search_results.html
│           └── status_badges.html
├── static/
│   └── css/
├── Dockerfile
├── docker-compose.yml       # Local dev
├── docker-compose.prod.yml  # Production/Portainer
├── requirements.txt
├── .env.example
└── README.md
```

## Data Flow

1. **Series Tracking**: User adds series via Settings page → stored in `tracked_series` table
2. **Pull-List Generation**:
   - Triggered manually or by scheduler
   - Queries Komga for new books from tracked series (last 7 days)
   - Optionally queries Mylar for upcoming releases
   - Creates Komga readlist with found books
   - Stores results in `weekly_books` and `pulllist_runs` tables
3. **Dashboard Display**: Reads from `weekly_books` table, shows cover grid with Komga links

## Recent Major Changes

### 2024-12-01 - Initial Project Setup
- **What**: Created complete project scaffold
- **Why**: New project initialization
- **Impact**: Full application structure with all core features
- **Components**:
  - FastAPI backend with async SQLAlchemy
  - Komga and Mylar API clients
  - HTMX-based dashboard with Tailwind CSS
  - APScheduler for automated runs
  - Docker configuration for Portainer deployment

## Known Limitations

- Mylar integration is optional (works without it)
- Series matching between Mylar and Komga is by ID only (manual linking)
- SQLite database (not suitable for high-concurrency, but fine for single-user)

## Future Considerations

- Add Mylar comic ID linking UI
- Cover image caching/proxy for auth
- Reading progress sync display
- Mobile-responsive improvements
- Notifications (email/webhook) on new pull-list
