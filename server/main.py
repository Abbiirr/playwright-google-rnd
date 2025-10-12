# main.py

"""
FastAPI Google Search API - Main Entry Point
"""

import sys
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.core.config import settings
from server.routers import search_router, job_router

# Fix for Windows asyncio + Playwright
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(search_router.router)
app.include_router(job_router.router)


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "endpoints": {
            "search": "/api/search",
            "batch_search": "/api/search/batch",
            "profiles": "/api/search/profiles",
            "async_batch": "/api/jobs/batch-async",
            "job_status": "/api/jobs/{job_id}",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from datetime import datetime
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.app_version
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )