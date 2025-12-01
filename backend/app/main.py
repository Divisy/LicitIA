"""FastAPI application entry point."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.scheduler import start_scheduler, shutdown_scheduler
from app.core.logging import setup_logging, get_logger
from app.api.v1 import health, tenders, subscriptions, experiences, leads, support, feedback
from app.services.tender_ingestion import fetch_and_store_new_tenders
from app.config import settings

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Log startup immediately
print("=" * 80)
print("LICITIA BACKEND STARTING")
print("=" * 80)

# Create FastAPI app
app = FastAPI(
    title="LicitIA API",
    description="API for road supervision tender alerts",
    version="1.0.0",
)

# CORS middleware (allow frontend to call backend)
# CORS origins - support both local and production
# Debug: Print ALL environment variables that start with CORS
print("=" * 80)
print("[CORS DEBUG] All CORS-related environment variables:")
for key, value in os.environ.items():
    if "CORS" in key.upper():
        print(f"  {key} = {value}")
print("=" * 80)

# Get CORS_ORIGINS from environment
cors_origins_raw = os.getenv("CORS_ORIGINS")
print(f"[CORS] Raw CORS_ORIGINS from env: {repr(cors_origins_raw)}")

# Default to localhost if not set
if not cors_origins_raw:
    print("[CORS] WARNING: CORS_ORIGINS not set, using defaults")
    cors_origins_str = "http://localhost:3000,http://localhost:5173"
else:
    cors_origins_str = cors_origins_raw

# Parse origins
cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

# Log CORS configuration for debugging (use both logger and print for visibility)
print(f"[CORS] CORS_ORIGINS env var: {cors_origins_raw if cors_origins_raw else 'NOT SET'}")
print(f"[CORS] Parsed CORS origins: {cors_origins}")
logger.info(f"CORS origins configured: {cors_origins}")
logger.info(f"CORS_ORIGINS env var: {cors_origins_raw if cors_origins_raw else 'NOT SET'}")

# If no CORS origins configured, use a fallback
# IMPORTANT: When allow_credentials=True, we CANNOT use allow_origins=["*"]
# We must specify explicit origins
if not cors_origins:
    logger.warning("No CORS origins configured, using fallback origins")
    # Fallback: allow common production and development origins
    cors_origins = [
        "https://perpetual-playfulness-production-c731.up.railway.app",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    print(f"[CORS] Using fallback origins: {cors_origins}")

# Configure CORS middleware
# Log the exact configuration being used
print(f"[CORS] Configuring middleware with origins: {cors_origins}")
logger.info(f"Configuring CORS middleware with origins: {cors_origins}")

# Add CORS middleware BEFORE routers
# IMPORTANT: When allow_credentials=True, allow_origins must be a list of specific origins, not ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,  # Always use explicit list, never ["*"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

print("[CORS] CORS middleware configured successfully")
logger.info("CORS middleware configured successfully")

# Add root endpoint for testing
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "LicitIA API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }

# Add CORS test endpoint
@app.get("/api/v1/cors-test")
async def cors_test():
    """Test endpoint to verify CORS is working."""
    return {
        "status": "ok",
        "cors": "configured",
        "message": "If you can see this, CORS is working!"
    }

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(tenders.router, prefix="/api/v1", tags=["tenders"])
app.include_router(subscriptions.router, prefix="/api/v1", tags=["subscriptions"])
app.include_router(experiences.router, prefix="/api/v1", tags=["experiences"])
app.include_router(leads.router, prefix="/api/v1", tags=["leads"])
app.include_router(support.router, prefix="/api/v1", tags=["support"])
app.include_router(feedback.router, prefix="/api/v1", tags=["feedback"])


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    print("[STARTUP] Initializing services...")
    logger.info("Application startup event triggered")
    
    try:
        start_scheduler()
        print("[STARTUP] Scheduler started")
        
        # Schedule the tender fetching job
        from apscheduler.triggers.interval import IntervalTrigger
        from app.core.scheduler import scheduler
        from datetime import datetime, timedelta
        
        # Don't run immediately on startup - wait 1 minute to let server fully start
        next_run = datetime.utcnow() + timedelta(minutes=1)
        
        scheduler.add_job(
            fetch_and_store_new_tenders,
            trigger=IntervalTrigger(hours=settings.FETCH_INTERVAL_HOURS),
            id="fetch_tenders",
            name="Fetch and store new tenders from SECOP",
            replace_existing=True,
            next_run_time=next_run,  # Wait 1 minute before first run
        )
        
        print(f"[STARTUP] Scheduled tender fetch job to run every {settings.FETCH_INTERVAL_HOURS} hours (first run in 1 minute)")
        logger.info(f"Scheduled tender fetch job to run every {settings.FETCH_INTERVAL_HOURS} hours (first run in 1 minute)")
        
        # NOTE: Semantic AI model will be loaded lazily on first use
        # This avoids downloading the model (~470MB) during startup/build
        # The model will be cached in memory after first load
        print("[STARTUP] Semantic AI model will be loaded on first use (lazy loading)")
        logger.info("Semantic AI model will be loaded on first use (lazy loading)")
        
        print("=" * 80)
        print("LICITIA BACKEND READY - Server is accepting requests")
        print("=" * 80)
        logger.info("Application startup completed successfully")
    except Exception as e:
        print(f"[STARTUP] ERROR during startup: {e}")
        logger.error(f"Error during startup: {e}", exc_info=True)
        # Don't raise - let server start even if startup tasks fail


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    shutdown_scheduler()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

