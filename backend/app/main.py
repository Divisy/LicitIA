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

# Create FastAPI app
app = FastAPI(
    title="LicitIA API",
    description="API for road supervision tender alerts",
    version="1.0.0",
)

# CORS middleware (allow frontend to call backend)
# CORS origins - support both local and production
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

# Log CORS configuration for debugging
logger.info(f"CORS origins configured: {cors_origins}")
logger.info(f"CORS_ORIGINS env var: {os.getenv('CORS_ORIGINS', 'NOT SET')}")

# If no CORS origins configured, allow all (for development)
# In production, always require explicit CORS_ORIGINS
if not cors_origins:
    logger.warning("No CORS origins configured, allowing all origins (development mode)")
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

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
    start_scheduler()
    
    # Schedule the tender fetching job
    from apscheduler.triggers.interval import IntervalTrigger
    from app.core.scheduler import scheduler
    from datetime import datetime
    
    # Add job that runs immediately on startup, then every 2 hours
    scheduler.add_job(
        fetch_and_store_new_tenders,
        trigger=IntervalTrigger(hours=settings.FETCH_INTERVAL_HOURS),
        id="fetch_tenders",
        name="Fetch and store new tenders from SECOP",
        replace_existing=True,
        next_run_time=datetime.utcnow(),  # Run immediately on startup
    )
    
    logger.info(f"Scheduled tender fetch job to run every {settings.FETCH_INTERVAL_HOURS} hours (starting immediately)")
    
    # Pre-load semantic AI model in background to avoid blocking first request
    import threading
    def preload_semantic_model():
        try:
            from app.services.experience_matching import get_semantic_model
            logger.info("Pre-loading semantic AI model in background...")
            model = get_semantic_model()
            if model:
                logger.info("Semantic AI model pre-loaded successfully")
            else:
                logger.warning("Semantic AI model not available")
        except Exception as e:
            logger.error(f"Error pre-loading semantic model: {e}")
    
    # Start pre-loading in background thread (non-blocking)
    threading.Thread(target=preload_semantic_model, daemon=True).start()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    shutdown_scheduler()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

