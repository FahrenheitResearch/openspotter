# OpenSpotter

An open-source storm spotter network platform for tracking severe weather spotters and reports in real-time.

## Features

- **Real-time Location Tracking**: Spotters share their GPS location via WebSocket
- **Weather Reports**: Submit and view severe weather reports (tornadoes, hail, flooding, etc.)
- **Interactive Map**: Leaflet-based map showing active spotters and reports
- **Chat/Messaging**: Real-time communication between spotters
- **Role-based Access**: Spotter, Verified Spotter, Coordinator, and Admin roles
- **Public API**: REST API with API key authentication for third-party integrations

## Tech Stack

### Backend
- Python 3.11+ with FastAPI
- PostgreSQL 16 with asyncpg
- Redis for caching and pub/sub
- SQLAlchemy 2.0 with async support
- JWT authentication

### Frontend
- React 18 with TypeScript
- Vite build tool
- Leaflet/React-Leaflet for maps
- TanStack Query for data fetching
- Zustand for state management
- Tailwind CSS for styling

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Using Docker (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/openspotter/openspotter.git
   cd openspotter
   ```

2. Copy the environment file:
   ```bash
   cp .env.example .env
   ```

3. Start all services:
   ```bash
   docker-compose up -d
   ```

4. Run database migrations:
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

5. Access the application:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/api/v1/docs

### Local Development

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set up database (requires PostgreSQL and Redis running)
alembic upgrade head

# Run development server
uvicorn app.main:app --reload
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
openspotter/
├── backend/
│   ├── app/
│   │   ├── api/           # API routes
│   │   │   └── v1/        # Versioned API endpoints
│   │   ├── core/          # Configuration, security, deps
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   └── services/      # Business logic
│   ├── alembic/           # Database migrations
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   ├── services/      # API and WebSocket services
│   │   └── store/         # Zustand stores
│   └── package.json
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
└── .env.example
```

## API Overview

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get tokens
- `POST /auth/refresh` - Refresh access token

### Users
- `GET /users/me` - Get current user
- `PUT /users/me` - Update current user
- `GET /users/{id}` - Get user by ID (admin)

### Locations
- `GET /locations/active` - Get active spotter locations (GeoJSON)
- `POST /locations/update` - Update own location
- `WS /locations/ws` - WebSocket for real-time location updates

### Reports
- `GET /reports` - List weather reports
- `POST /reports` - Create new report
- `GET /reports/geojson` - Get reports as GeoJSON
- `PUT /reports/{id}/verify` - Verify report (coordinator+)

### Messages
- `GET /messages/channels` - List channels
- `GET /messages/channels/{id}/messages` - Get channel messages
- `POST /messages` - Send message
- `WS /messages/ws` - WebSocket for real-time chat

### Public API (v1)
- `GET /api/v1/spotters` - Get active spotters
- `GET /api/v1/reports` - Get weather reports
- `GET /api/v1/reports/geojson` - Reports as GeoJSON

## User Roles

| Role | Permissions |
|------|-------------|
| `spotter` | Submit reports, share location, chat |
| `verified_spotter` | All spotter permissions + visible on public API |
| `coordinator` | Verify reports, moderate chat, manage spotters |
| `admin` | Full system access, manage users and API keys |

## Configuration

See `.env.example` for all configuration options. Key settings:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing key (change in production!) |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `DEBUG` | Enable debug mode |
| `CORS_ORIGINS` | Allowed CORS origins |

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -m 'Add my feature'`
4. Push to branch: `git push origin feature/my-feature`
5. Open a pull request

## License

MIT License - see LICENSE file for details.
