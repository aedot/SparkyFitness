"""
Whoop Microservice - Main Application
Entry point for FastAPI application
"""

import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Import route modules
from routes import auth, health, activities

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Whoop Microservice",
    description="Integrates Whoop API with SparkyFitness",
    version="1.0.0"
)

# Get port from environment variable or use default
PORT = int(os.getenv("WHOOP_SERVICE_PORT", 9000))

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth/whoop", tags=["Authentication"])
app.include_router(health.router, prefix="/data", tags=["Health & Wellness"])
app.include_router(activities.router, prefix="/data", tags=["Activities"])

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Whoop Microservice is running!",
        "status": "healthy",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Kubernetes/Docker health check"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("WHOOP_SERVICE_PORT", 9000))
    logger.info(f"Starting Whoop microservice on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)