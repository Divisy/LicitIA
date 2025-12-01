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
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

# Log CORS configuration for debugging (use both logger and print for visibility)
print(f"[CORS] CORS_ORIGINS env var: {os.getenv('CORS_ORIGINS', 'NOT SET')}")
print(f"[CORS] CORS origins configured: {cors_origins}")
logger.info(f"CORS origins configured: {cors_origins}")
logger.info(f"CORS_ORIGINS env var: {os.getenv('CORS_ORIGINS', 'NOT SET')}")

# If no CORS origins configured, allow all (for development)
# In production, always require explicit CORS_ORIGINS
if not cors_origins:
    logger.warning("No CORS origins configured, allowing all origins (development mode)")
    cors_origins = ["*"]

# Configure CORS middleware
# Log the exact configuration being used
print(f"[CORS] Configuring middleware with origins: {cors_origins}")
logger.info(f"Configuring CORS middleware with origins: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

print("[CORS] CORS middleware configured successfully")
logger.info("CORS middleware configured successfully")

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
        
        # Pre-load semantic AI model in background to avoid blocking first request
        import threading
        def preload_semantic_model():
            try:
                from app.services.experience_matching import get_semantic_model
                print("[STARTUP] Pre-loading semantic AI model in background...")
                logger.info("Pre-loading semantic AI model in background...")
                model = get_semantic_model()
                if model:
                    print("[STARTUP] Semantic AI model pre-loaded successfully")
                    logger.info("Semantic AI model pre-loaded successfully")
                else:
                    print("[STARTUP] Semantic AI model not available")
                    logger.warning("Semantic AI model not available")
            except Exception as e:
                print(f"[STARTUP] Error pre-loading semantic model: {e}")
                logger.error(f"Error pre-loading semantic model: {e}")
        
        # Start pre-loading in background thread (non-blocking)
        threading.Thread(target=preload_semantic_model, daemon=True).start()
        print("[STARTUP] Background model pre-loading started")
        
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

