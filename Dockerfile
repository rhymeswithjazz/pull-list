# Wednesday Dockerfile
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    PUID=1000 \
    PGID=1000

# Set work directory
WORKDIR /app

# Install gosu for user switching
RUN apt-get update && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies first (for layer caching)
COPY pyproject.toml .
RUN uv pip install --system -r pyproject.toml

# Copy application code
COPY app/ ./app/
COPY static/ ./static/

# Create data directory for SQLite database
RUN mkdir -p /app/data

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run entrypoint
ENTRYPOINT ["/entrypoint.sh"]
