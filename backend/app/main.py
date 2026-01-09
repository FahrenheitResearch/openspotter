from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis

from app.config import get_settings
from app.database import init_db
from app.routers import auth, users, reports, locations, messages, api_v1

settings = get_settings()

# Redis connection pool
redis_pool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global redis_pool

    # Startup
    print(f"Starting {settings.app_name} v{settings.app_version}")

    # Initialize database tables
    await init_db()
    print("Database initialized")

    # Initialize Redis connection (optional for local dev)
    try:
        redis_pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
        )
        app.state.redis = redis.Redis(connection_pool=redis_pool)
        # Test connection
        await app.state.redis.ping()
        print("Redis connected")
    except Exception as e:
        print(f"Redis not available (optional): {e}")
        app.state.redis = None

    yield

    # Shutdown
    if redis_pool:
        try:
            await redis_pool.disconnect()
        except Exception:
            pass
    print("Shutdown complete")


app = FastAPI(
    title=settings.app_name,
    description="""
    OpenSpotter - Open Source Spotter Network

    A community-driven, open-source alternative to proprietary spotter networks.

    ## Features
    - Real-time spotter location sharing
    - Weather report submission and verification
    - Coordinator chat and messaging
    - Open API for third-party integration

    ## Community Principles
    - **Data Ownership**: You own your data
    - **Open API**: Free integration with any weather app
    - **Self-Hostable**: Run your own instance
    - **Community Governed**: Open development
    """,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(reports.router, prefix="/reports", tags=["Weather Reports"])
app.include_router(locations.router, prefix="/locations", tags=["Locations"])
app.include_router(messages.router, prefix="/messages", tags=["Messages"])
app.include_router(api_v1.router, prefix="/api/v1", tags=["Public API v1"])


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - basic health check."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "healthy",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected",
    }
