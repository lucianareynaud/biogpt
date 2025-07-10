"""
Main FastAPI application for Genomic-LLM.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import logging
from contextlib import asynccontextmanager

from app.routers import genome_upload, report, chat
from app.dependencies import get_database, get_vector_store

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Genomic-LLM API...")
    
    # Initialize database and vector store connections
    try:
        database = get_database()
        vector_store = get_vector_store()
        logger.info("Database and vector store initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise e
    
    yield
    
    logger.info("Shutting down Genomic-LLM API...")

app = FastAPI(
    title="Genomic-LLM API",
    description="MVP SaaS for genomic analysis with PubMedBERT",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(genome_upload.router, prefix="/api/v1", tags=["genome"])
app.include_router(report.router, prefix="/api/v1", tags=["reports"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Genomic-LLM API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/healthz")
async def health_check():
    """Health check endpoint for container orchestration."""
    try:
        # Test database connection
        database = get_database()
        
        # Test vector store connection
        vector_store = get_vector_store()
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "database": "connected",
                "vector_store": "connected",
                "version": "1.0.0"
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )

@app.get("/info")
async def app_info():
    """Application information endpoint."""
    return {
        "name": "Genomic-LLM",
        "version": "1.0.0",
        "description": "MVP SaaS para análise genômica com IA",
        "features": [
            "Upload de arquivos 23andMe (.txt)",
            "Classificação ACMG-2015 simplificada",
            "Geração de laudos em PDF",
            "Chat explicativo com RAG",
            "Integração ClinVar/gnomAD"
        ],
        "endpoints": {
            "upload": "/api/v1/genome-upload",
            "reports": "/api/v1/reports",
            "chat": "/api/v1/chat"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=os.getenv("RELOAD", "false").lower() == "true"
    ) 