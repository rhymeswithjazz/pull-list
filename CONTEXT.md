# Wednesday - Project Context

## Project Overview

Wednesday is a comic book pull-list dashboard that integrates with self-hosted Mylar3 and Komga instances. It allows users to track specific comic series and generates weekly reading lists with a visual cover grid interface.

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
- **Frontend**: HTMX 1.9.x + Alpine.js 3.x + Jinja2 templates + Tailwind CSS (CDN)
- **Database**: SQLite with SQLAlchemy 2.x (async)
- **Scheduling**: APScheduler 3.10.x
- **HTTP Client**: httpx 0.28.x
- **Build Tools**: Docker with buildx (multi-platform)
- **Deployment**: Docker container via Portainer
- **Container Registry**: DockerHub (`rhymeswithjazz/pull-list`)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Wednesday App                          │
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
│  │   ├── WeeklyBook                                         │
│  │   ├── User, MagicLinkToken                               │
│  │   └── NotificationLog                                    │
│  └── Scheduler (APScheduler)                                │
│       └── Daily cron job (configurable)                     │
├─────────────────────────────────────────────────────────────┤
│  External Services                                           │
│  ├── Komga API (required)                                   │
│  │   ├── GET /api/v1/series - List/search series           │
│  │   ├── GET /api/v1/series/{id}/books - Get books         │
│  │   ├── GET /api/v1/books/{id} - Get book with progress   │
│  │   ├── GET /api/v1/books/{id}/file - Download book file  │
│  │   ├── PATCH /api/v1/books/{id}/read-progress - Mark read│
│  │   ├── DELETE /api/v1/books/{id}/read-progress - Clear   │
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
│   ├── dependencies.py      # FastAPI auth dependencies
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth.py          # Authentication service
│   │   ├── email.py         # SMTP email service
│   │   ├── mylar.py         # Mylar API client
│   │   ├── komga.py         # Komga API client
│   │   └── pulllist.py      # Core pull-list logic
│   └── templates/
│       ├── base.html
│       ├── dashboard.html
│       ├── login.html           # Login page
│       ├── setup.html           # Initial setup page
│       ├── forgot_password.html # Password reset request
│       ├── reset_password.html  # Password reset form
│       ├── logs.html            # Run history + status lights
│       ├── settings.html
│       └── partials/
│           ├── book_card.html
│           ├── pull_list_grid.html
│           ├── tracked_series_list.html
│           ├── series_search_results.html
│           └── status_badges.html
├── static/
│   └── css/
├── Dockerfile
├── entrypoint.sh            # PUID/PGID user setup
├── docker-compose.yml       # Local dev
├── docker-compose.prod.yml  # Production/Portainer
├── pyproject.toml
├── .env.example
└── README.md
```

## Data Flow

1. **Series Tracking**: User adds series via Settings page → stored in `tracked_series` table
2. **Wednesday Generation**:
   - Triggered manually or by scheduler
   - Queries Komga for new books from tracked series (last 7 days)
   - Optionally queries Mylar for upcoming releases
   - Creates Komga readlist with found books
   - Stores results in `weekly_books` and `pulllist_runs` tables
3. **Dashboard Display**: 
   - Reads from `weekly_books` table
   - Fetches fresh read progress from Komga API
   - Shows cover grid with status badges and progress bars

## Recent Major Changes

### 2025-12-05 - Mark Read/Unread & Download Actions
- **What**: Added ability to mark books as read/unread and download for offline reading
- **Why**: Allow users to manage read status directly from dashboard without opening Komga
- **Impact**: Each book card now has a dropdown menu with Mark Read, Mark Unread, and Download options
- **Changes**:
  - New KomgaClient methods: `mark_book_read()`, `mark_book_unread()`, `get_book_file()`
  - New API endpoints: `POST /api/book/{id}/mark-read`, `POST /api/book/{id}/mark-unread`, `GET /api/book/{id}/download`
  - New partial template: `book_card.html` with Alpine.js dropdown menu
  - Added Alpine.js to base template for interactive UI components
  - Refactored `pull_list_grid.html` to use book_card partial
  - Mark Read disabled when book is already fully read
  - Mark Unread disabled when book has no reading progress

### 2025-12-01 - Email Notifications & Password Reset
- **What**: Added email notifications for new pull-lists and password reset flow
- **Why**: Get notified when comics are available; recover forgotten passwords
- **Impact**:
  - Receive one email per week when new comics first appear
  - Users can reset passwords via email link
- **Changes**:
  - New model: `NotificationLog` tracks sent notifications per week
  - Added `send_pulllist_notification_email()` to email service
  - Scheduler checks `NotificationLog` before sending (prevents duplicates)
  - Password reset flow: `/forgot-password`, `/reset-password/{token}`
  - New templates: `forgot_password.html`, `reset_password.html`
  - Scheduler now runs daily by default (configurable via `SCHEDULE_DAY_OF_WEEK`)
  - New config: `NOTIFICATION_EMAIL` - where to send pull-list alerts
  - Moved Komga/Mylar status lights from header to Logs page

### 2025-12-01 - User Authentication
- **What**: Added username/password and magic link authentication
- **Why**: Protect the application from unauthorized access
- **Impact**: All routes now require authentication except login/setup/health
- **Changes**:
  - New models: `User`, `MagicLinkToken` in `models.py`
  - New services: `app/services/auth.py` (JWT, password hashing, magic links)
  - New services: `app/services/email.py` (SMTP for magic link emails)
  - New dependency: `app/dependencies.py` (get_current_user)
  - New templates: `login.html`, `setup.html`
  - New routes: `/login`, `/setup`, `/api/auth/*`, `/auth/magic-link/{token}`
  - All existing routes now protected with `Depends(get_current_user)`
  - JWT tokens stored in httpOnly cookies (24-hour expiry)
  - Magic link tokens single-use, 15-minute expiry
  - First-run setup flow creates admin user
  - New dependencies: bcrypt, python-jose, aiosmtplib, email-validator

### 2025-12-01 - Read Progress Tracking & Docker Improvements
- **What**: Added real-time read progress from Komga, improved Docker deployment
- **Why**: Better visibility into reading status, easier NAS deployment
- **Impact**: Dashboard now shows read percentage and progress bars
- **Changes**:
  - Added `pages_count`, `pages_read`, `read_percentage` to `KomgaBook`
  - Added `get_book_by_id` and `get_books_by_ids` to `KomgaClient`
  - Dashboard fetches fresh read progress on each load
  - Status badges: "Read" (green), "42%" (purple), "Unread" (blue), "Upcoming" (yellow)
  - Progress bar overlay on covers for books in progress
  - Fixed dashboard layout: sticky footer, scrollable content area
  - Docker: PUID/PGID support for Synology NAS (default 1026/100)
  - Docker: Changed port to 8282
  - Docker: Bind mount to `/volume1/docker/pull-list` for data
  - Published to DockerHub: `rhymeswithjazz/pull-list:latest` (amd64)

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

## Docker Deployment

### Environment Variables
```bash
PUID=1026                    # User ID for file permissions
PGID=100                     # Group ID for file permissions
KOMGA_URL=http://komga:25600
KOMGA_USERNAME=user
KOMGA_PASSWORD=pass
MYLAR_URL=http://mylar:8090  # Optional
MYLAR_API_KEY=xxx            # Optional
TIMEZONE=America/New_York

# Authentication
SECRET_KEY=your-secure-random-key
APP_URL=https://pulllist.example.com

# SMTP (optional, for magic link auth and notifications)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=user@example.com
SMTP_PASSWORD=your-password
SMTP_FROM_EMAIL=pulllist@example.com
SMTP_USE_TLS=true

# Notifications (requires SMTP)
NOTIFICATION_EMAIL=you@example.com

# Schedule (default: daily at 10am)
SCHEDULE_DAY_OF_WEEK=*       # "*" = daily, "wed" = Wednesday only
SCHEDULE_HOUR=10
SCHEDULE_MINUTE=0
```

### Volume Mount
```yaml
volumes:
  - /volume1/docker/pull-list:/app/data
```

### Build & Push
```bash
docker buildx build --platform linux/amd64 -t rhymeswithjazz/pull-list:latest --push .
```

## Known Limitations

- Mylar integration is optional (works without it)
- Series matching between Mylar and Komga is by ID only (manual linking)
- SQLite database (not suitable for high-concurrency, but fine for single-user)
- Read progress requires Komga to be accessible on dashboard load

## Future Considerations

- Add Mylar comic ID linking UI
- Cover image caching/proxy for auth
- Mobile-responsive improvements
- Webhook notifications (Discord, Slack, etc.)
