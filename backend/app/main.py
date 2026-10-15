"""
FinancialWatch FastAPI Application Entrypoint.
Orchestrates multi-agent pipelines, human-in-the-loop queue, and knowledge base status.
"""
import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

load_dotenv()

from backend.app.api import kb, narratives, posts, queue, risk

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("financial_watch.main")

app = FastAPI(
    title="FinancialWatch API",
    description="AI-Driven Misinformation & Reputational Risk Intelligence for Nigerian Financial Institutions",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
raw_origins = os.getenv("CORS_ORIGINS", "*")
if raw_origins == "*":
    cors_origins = ["*"]
    cors_credentials = False
else:
    cors_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
    cors_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(posts.router)
app.include_router(queue.router)
app.include_router(narratives.router)
app.include_router(risk.router)
app.include_router(kb.router)

@app.get("/health", tags=["Health"])
async def health_check():
    """Service liveness probe."""
    return {"status": "ok", "service": "financial-watch-backend", "version": "1.0.0"}

# Single-origin static frontend fallback
# If Next.js static export 'frontend/out' exists, serve it directly from FastAPI
frontend_out = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "out")
if os.path.exists(frontend_out):
    logger.info(f"Mounting static export frontend from {frontend_out}")
    app.mount("/", StaticFiles(directory=frontend_out, html=True), name="frontend")
else:
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": "FinancialWatch API",
            "documentation": "/docs",
            "status": "active",
            "note": "Frontend static bundle not mounted. Run frontend separately or build static export."
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
