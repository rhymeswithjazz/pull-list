# Pull-List

A comic book pull-list dashboard that integrates with Mylar3 and Komga to create weekly reading lists.

## Features

- **Weekly Pull-List Dashboard**: Visual grid of comic covers for your tracked series
- **Komga Integration**: Automatically creates reading lists in Komga
- **Mylar3 Integration**: Shows upcoming releases (optional)
- **Scheduled Generation**: Automatically runs on your schedule (default: Wednesdays)
- **Manual Trigger**: Generate pull-lists on demand with a single click
- **Series Management**: Add/remove series to track from your Komga library

## Quick Start

### Docker (Recommended)

1. Copy the environment file and configure:
   ```bash
   cp .env.example .env
   # Edit .env with your Komga and Mylar credentials
   ```

2. Build and run:
   ```bash
   docker compose up -d
   ```

3. Open http://localhost:8000

### Local Development

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `KOMGA_URL` | Komga server URL | `http://localhost:25600` |
| `KOMGA_USERNAME` | Komga username | - |
| `KOMGA_PASSWORD` | Komga password | - |
| `KOMGA_API_KEY` | Komga API key (alternative to user/pass) | - |
| `MYLAR_URL` | Mylar3 server URL | `http://localhost:8090` |
| `MYLAR_API_KEY` | Mylar3 API key | - |
| `SCHEDULE_DAY_OF_WEEK` | Day to run scheduled job | `wed` |
| `SCHEDULE_HOUR` | Hour to run (24h format) | `10` |
| `SCHEDULE_MINUTE` | Minute to run | `0` |
| `TIMEZONE` | Timezone for schedule | `America/New_York` |

## Portainer Deployment

1. Build and push the image:
   ```bash
   docker build -t yourusername/pull-list:latest .
   docker push yourusername/pull-list:latest
   ```

2. In Portainer, create a new stack using `docker-compose.prod.yml`

3. Configure environment variables in the Portainer UI

4. If Mylar and Komga are on a custom Docker network, update the `networks` section

## Usage

1. **Add Series**: Go to Settings and search for series from your Komga library
2. **Generate Pull-List**: Click "Generate Now" or wait for the scheduled run
3. **Read Comics**: Click any cover to open it directly in Komga

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: HTMX + Jinja2 + Tailwind CSS
- **Database**: SQLite
- **Scheduling**: APScheduler
- **Container**: Docker

## License

MIT
