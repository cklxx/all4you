"""
Qwen3 Fine-tuner Backend Application
Main FastAPI application entry point
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from api import router as api_router
from core.config import Settings
from core.database import init_db, get_db_session

# Initialize logger
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
logger.add(
    log_dir / "app.log",
    rotation="500 MB",
    retention="10 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

# Load settings
settings = Settings()

# Database initialization
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info("Starting Qwen3 Fine-tuner API...")
    init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down...")

# Create FastAPI app
app = FastAPI(
    title="Qwen3 Fine-tuner API",
    description="Professional fine-tuning platform for Qwen3 models",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix="/api")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "qwen3-finetuner",
        "version": "0.1.0"
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Qwen3 Fine-tuner",
        "description": "Professional fine-tuning platform for Qwen3 models",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server on {settings.HOST}:{settings.PORT}")
    logger.info(f"API docs available at http://{settings.HOST}:{settings.PORT}/docs")

    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
