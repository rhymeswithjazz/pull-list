"""FastAPI application for the pull-list dashboard."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db, init_db
from app.dependencies import get_current_user, get_current_user_optional
from app.models import User
from app.scheduler import (
    get_next_run_time,
    setup_scheduler,
    shutdown_scheduler,
    start_scheduler,
)
from app.services.auth import (
    authenticate_user,
    create_access_token,
    create_magic_link_token,
    create_user,
    get_user_by_email,
    get_user_count,
    update_user_password,
    verify_magic_link_token,
)
from app.services.email import send_magic_link_email, send_password_reset_email
from app.services.komga import KomgaClient
from app.services.mylar import MylarClient
from app.services.pulllist import (
    PullListService,
    format_week_display,
    get_current_week_id,
    get_next_week_id,
    get_previous_week_id,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Pull-List application")
    await init_db()
    setup_scheduler()
    start_scheduler()
    yield
    # Shutdown
    shutdown_scheduler()
    logger.info("Pull-List application stopped")


app = FastAPI(
    title="Pull-List",
    description="Comic book pull-list dashboard",
    version="0.1.0",
    lifespan=lifespan,
)

# Mount static files
static_path = Path(__file__).parent.parent / "static"
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Setup templates
templates_path = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=templates_path)

settings = get_settings()


# Template context helpers
def get_base_context(request: Request, user: User | None = None) -> dict:
    """Get base context for templates."""
    return {
        "request": request,
        "week_id": get_current_week_id(),
        "next_run": get_next_run_time(),
        "komga_url": settings.komga_url,
        "user": user,
        "smtp_configured": settings.smtp_configured,
    }


# Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    week: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Main dashboard showing the weekly pull-list."""
    service = PullListService(db)

    # Determine which week to show
    current_week_id = get_current_week_id()
    display_week_id = week if week else current_week_id
    is_current_week = display_week_id == current_week_id

    # Get tracked series and week data
    tracked_series = await service.get_tracked_series()
    weekly_books = await service.get_week_books(display_week_id)
    available_weeks = await service.get_available_weeks()
    week_readlist = await service.get_readlist_for_week(display_week_id)

    # Calculate navigation
    prev_week_id = get_previous_week_id(display_week_id)
    next_week_id = get_next_week_id(display_week_id)

    # Check if prev/next weeks have data or are current week
    has_prev_week = prev_week_id in available_weeks
    has_next_week = next_week_id in available_weeks or next_week_id == current_week_id

    # Don't allow navigating past current week
    if display_week_id >= current_week_id:
        has_next_week = False

    # Fetch fresh read progress from Komga for all books
    book_ids = [book.komga_book_id for book in weekly_books]
    komga_books: dict = {}
    if book_ids:
        try:
            async with KomgaClient() as komga:
                komga_books = await komga.get_books_by_ids(book_ids)
        except Exception:
            pass  # Fall back to database values if Komga is unavailable

    # Build pull list items from weekly books
    pull_list_items = []
    for book in weekly_books:
        # Get fresh read progress from Komga if available
        komga_book = komga_books.get(book.komga_book_id)
        is_read = komga_book.is_read if komga_book else book.is_read
        read_percentage = komga_book.read_percentage if komga_book else 0

        pull_list_items.append({
            "series_name": book.series_name,
            "book_number": book.book_number,
            "book_title": book.book_title,
            "is_downloaded": True,
            "is_read": is_read,
            "read_percentage": read_percentage,
            "thumbnail_url": f"/api/proxy/book/{book.komga_book_id}/thumbnail",
            "read_url": f"{settings.komga_url}/book/{book.komga_book_id}/read",
            "komga_book_id": book.komga_book_id,
        })

    context = get_base_context(request, user)
    context.update({
        "pull_list": pull_list_items,
        "tracked_series": tracked_series,
        "tracked_count": len(tracked_series),
        "books_count": len(pull_list_items),
        # Week navigation
        "display_week_id": display_week_id,
        "week_display": format_week_display(display_week_id),
        "is_current_week": is_current_week,
        "prev_week_id": prev_week_id if has_prev_week else None,
        "next_week_id": next_week_id if has_next_week else None,
        "available_weeks": available_weeks,
        "week_readlist": week_readlist,
    })

    return templates.TemplateResponse("dashboard.html", context)


@app.post("/api/run-now", response_class=HTMLResponse)
async def run_now(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Manually trigger pull-list generation."""
    service = PullListService(db)

    result = await service.generate_pulllist(
        run_type="manual",
        days_back=7,
        create_readlist=True,
    )

    # Build response items
    pull_list_items = []
    for item in result.items:
        pull_list_items.append({
            "series_name": item.series_name,
            "book_number": item.book_number,
            "book_title": item.book_title,
            "is_downloaded": item.is_downloaded,
            "is_read": item.is_read,
            "read_percentage": item.read_percentage,
            "thumbnail_url": item.thumbnail_url,
            "read_url": item.read_url,
            "komga_book_id": item.komga_book_id,
            "release_date": item.release_date,
        })

    context = get_base_context(request, user)
    context.update({
        "pull_list": pull_list_items,
        "result": result,
        "success": result.success,
        "error": result.error,
    })

    return templates.TemplateResponse("partials/pull_list_grid.html", context)


@app.get("/logs", response_class=HTMLResponse)
async def logs_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Logs page showing run history."""
    service = PullListService(db)
    recent_runs = await service.get_recent_runs(limit=50)

    context = get_base_context(request, user)
    context.update({
        "recent_runs": recent_runs,
    })

    return templates.TemplateResponse("logs.html", context)


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Settings page for managing tracked series."""
    service = PullListService(db)
    tracked_series = await service.get_tracked_series(active_only=False)

    context = get_base_context(request, user)
    context.update({
        "tracked_series": tracked_series,
    })

    return templates.TemplateResponse("settings.html", context)


@app.post("/api/series/search", response_class=HTMLResponse)
async def search_series(
    request: Request,
    query: str = Form(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Search Komga for series to add."""
    async with KomgaClient() as komga:
        series_list = await komga.get_series(search=query)

    # Get already tracked series IDs
    service = PullListService(db)
    tracked_series = await service.get_tracked_series(active_only=False)
    tracked_ids = {s.komga_series_id for s in tracked_series}

    context = get_base_context(request, user)
    context.update({
        "search_results": series_list,
        "query": query,
        "tracked_ids": tracked_ids,
    })

    return templates.TemplateResponse("partials/series_search_results.html", context)


@app.post("/api/series/add", response_class=HTMLResponse)
async def add_series(
    request: Request,
    komga_series_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Add a series to tracking."""
    async with KomgaClient() as komga:
        series = await komga.get_series_by_id(komga_series_id)

    service = PullListService(db)
    await service.add_tracked_series(
        name=series.name,
        komga_series_id=series.id,
        publisher=series.publisher,
    )

    # Return updated tracked series list
    tracked_series = await service.get_tracked_series(active_only=False)

    context = get_base_context(request, user)
    context.update({
        "tracked_series": tracked_series,
    })

    return templates.TemplateResponse("partials/tracked_series_list.html", context)


@app.post("/api/series/{series_id}/toggle", response_class=HTMLResponse)
async def toggle_series(
    request: Request,
    series_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Toggle a series active status."""
    service = PullListService(db)
    await service.toggle_tracked_series(series_id)

    tracked_series = await service.get_tracked_series(active_only=False)

    context = get_base_context(request, user)
    context.update({
        "tracked_series": tracked_series,
    })

    return templates.TemplateResponse("partials/tracked_series_list.html", context)


@app.delete("/api/series/{series_id}", response_class=HTMLResponse)
async def delete_series(
    request: Request,
    series_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Remove a series from tracking."""
    service = PullListService(db)
    await service.remove_tracked_series(series_id)

    tracked_series = await service.get_tracked_series(active_only=False)

    context = get_base_context(request, user)
    context.update({
        "tracked_series": tracked_series,
    })

    return templates.TemplateResponse("partials/tracked_series_list.html", context)


@app.get("/api/status", response_class=HTMLResponse)
async def get_status(
    request: Request,
    user: User = Depends(get_current_user),
):
    """Get connection status for Mylar and Komga."""
    mylar_status = False
    komga_status = False

    try:
        async with MylarClient() as mylar:
            mylar_status = await mylar.test_connection()
    except Exception:
        pass

    try:
        async with KomgaClient() as komga:
            komga_status = await komga.test_connection()
    except Exception:
        pass

    context = get_base_context(request, user)
    context.update({
        "mylar_status": mylar_status,
        "komga_status": komga_status,
    })

    return templates.TemplateResponse("partials/status_badges.html", context)


@app.post("/api/week/{week_id}/clear", response_class=HTMLResponse)
async def clear_week(
    request: Request,
    week_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Clear all books for a specific week."""
    service = PullListService(db)
    await service.clear_week_books(week_id)

    # Redirect back to dashboard
    return RedirectResponse(url="/", status_code=303)


@app.get("/api/proxy/book/{book_id}/thumbnail")
async def proxy_book_thumbnail(
    book_id: str,
    user: User = Depends(get_current_user),
):
    """Proxy book thumbnail from Komga with authentication."""
    async with KomgaClient() as komga:
        url = f"/api/v1/books/{book_id}/thumbnail"
        try:
            response = await komga._client.get(f"{komga.base_url}{url}")
            response.raise_for_status()
            return Response(
                content=response.content,
                media_type=response.headers.get("content-type", "image/jpeg"),
                headers={"Cache-Control": "public, max-age=86400"},
            )
        except Exception:
            raise HTTPException(status_code=404, detail="Thumbnail not found")


@app.get("/api/proxy/series/{series_id}/thumbnail")
async def proxy_series_thumbnail(
    series_id: str,
    user: User = Depends(get_current_user),
):
    """Proxy series thumbnail from Komga with authentication."""
    async with KomgaClient() as komga:
        url = f"/api/v1/series/{series_id}/thumbnail"
        try:
            response = await komga._client.get(f"{komga.base_url}{url}")
            response.raise_for_status()
            return Response(
                content=response.content,
                media_type=response.headers.get("content-type", "image/jpeg"),
                headers={"Cache-Control": "public, max-age=86400"},
            )
        except Exception:
            raise HTTPException(status_code=404, detail="Thumbnail not found")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# =============================================================================
# Authentication Routes
# =============================================================================


@app.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    """Login page."""
    # If already logged in, redirect to dashboard
    if user:
        return RedirectResponse(url="/", status_code=303)

    # If no users exist, redirect to setup
    user_count = await get_user_count(db)
    if user_count == 0:
        return RedirectResponse(url="/setup", status_code=303)

    context = {
        "request": request,
        "smtp_configured": settings.smtp_configured,
    }
    return templates.TemplateResponse("login.html", context)


@app.post("/api/auth/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle login form submission."""
    user = await authenticate_user(db, username, password)

    if not user:
        # Return error for HTMX
        context = {
            "request": request,
            "error": "Invalid username or password",
            "smtp_configured": settings.smtp_configured,
        }
        return templates.TemplateResponse(
            "login.html",
            context,
            status_code=401,
        )

    # Create access token
    access_token = create_access_token(user.id)

    # Set cookie and redirect
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return response


@app.post("/api/auth/magic-link", response_class=HTMLResponse)
async def request_magic_link(
    request: Request,
    email: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Request a magic link login email."""
    # Always show success message to prevent email enumeration
    context = {
        "request": request,
        "magic_link_sent": True,
        "smtp_configured": settings.smtp_configured,
    }

    user = await get_user_by_email(db, email)
    if user and user.is_active:
        # Create magic link token
        token = await create_magic_link_token(db, user.id)
        # Send email (fire and forget - we don't wait for success)
        await send_magic_link_email(email, token)

    return templates.TemplateResponse("login.html", context)


@app.get("/auth/magic-link/{token}")
async def verify_magic_link(
    request: Request,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Verify a magic link token and log the user in."""
    user = await verify_magic_link_token(db, token)

    if not user:
        # Invalid or expired token
        context = {
            "request": request,
            "error": "Invalid or expired magic link. Please request a new one.",
            "smtp_configured": settings.smtp_configured,
        }
        return templates.TemplateResponse("login.html", context, status_code=400)

    # Create access token
    access_token = create_access_token(user.id)

    # Set cookie and redirect
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return response


@app.post("/api/auth/logout")
async def logout(request: Request):
    """Log the user out by clearing the access token cookie."""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="access_token")
    return response


@app.get("/setup", response_class=HTMLResponse)
async def setup_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Initial setup page - create first user."""
    # If users exist, redirect to login
    user_count = await get_user_count(db)
    if user_count > 0:
        return RedirectResponse(url="/login", status_code=303)

    context = {"request": request}
    return templates.TemplateResponse("setup.html", context)


@app.post("/api/auth/setup")
async def setup_create_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Create the initial user during setup."""
    # Check if users already exist
    user_count = await get_user_count(db)
    if user_count > 0:
        return RedirectResponse(url="/login", status_code=303)

    # Basic validation
    if len(username) < 3:
        context = {
            "request": request,
            "error": "Username must be at least 3 characters",
        }
        return templates.TemplateResponse("setup.html", context, status_code=400)

    if len(password) < 8:
        context = {
            "request": request,
            "error": "Password must be at least 8 characters",
        }
        return templates.TemplateResponse("setup.html", context, status_code=400)

    # Create user
    user = await create_user(db, username, email, password)

    # Log them in
    access_token = create_access_token(user.id)

    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    return response


@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    """Forgot password page."""
    if not settings.smtp_configured:
        # Redirect to login if SMTP not configured
        return RedirectResponse(url="/login", status_code=303)

    context = {"request": request}
    return templates.TemplateResponse("forgot_password.html", context)


@app.post("/api/auth/forgot-password", response_class=HTMLResponse)
async def forgot_password(
    request: Request,
    email: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Request a password reset email."""
    # Always show success message to prevent email enumeration
    context = {
        "request": request,
        "reset_sent": True,
    }

    user = await get_user_by_email(db, email)
    if user and user.is_active:
        # Create magic link token (reuse for password reset)
        token = await create_magic_link_token(db, user.id)
        await send_password_reset_email(email, token)

    return templates.TemplateResponse("forgot_password.html", context)


@app.get("/reset-password/{token}", response_class=HTMLResponse)
async def reset_password_page(
    request: Request,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Password reset form page."""
    # Verify token is valid (but don't consume it yet)
    from sqlalchemy import select

    from app.models import MagicLinkToken
    from app.services.auth import utcnow

    result = await db.execute(
        select(MagicLinkToken).where(MagicLinkToken.token == token)
    )
    magic_token = result.scalar_one_or_none()

    if not magic_token or magic_token.used_at or magic_token.expires_at < utcnow():
        context = {
            "request": request,
            "error": "Invalid or expired reset link. Please request a new one.",
            "smtp_configured": settings.smtp_configured,
        }
        return templates.TemplateResponse("login.html", context, status_code=400)

    context = {
        "request": request,
        "token": token,
    }
    return templates.TemplateResponse("reset_password.html", context)


@app.post("/api/auth/reset-password/{token}", response_class=HTMLResponse)
async def reset_password(
    request: Request,
    token: str,
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Process password reset."""
    # Verify and consume the token
    user = await verify_magic_link_token(db, token)

    if not user:
        context = {
            "request": request,
            "error": "Invalid or expired reset link. Please request a new one.",
            "smtp_configured": settings.smtp_configured,
        }
        return templates.TemplateResponse("login.html", context, status_code=400)

    # Validate password
    if len(password) < 8:
        context = {
            "request": request,
            "token": token,
            "error": "Password must be at least 8 characters",
        }
        return templates.TemplateResponse("reset_password.html", context, status_code=400)

    # Update password
    await update_user_password(db, user.id, password)

    # Redirect to login with success message
    context = {
        "request": request,
        "success": "Password reset successfully. Please log in with your new password.",
        "smtp_configured": settings.smtp_configured,
    }
    return templates.TemplateResponse("login.html", context)
