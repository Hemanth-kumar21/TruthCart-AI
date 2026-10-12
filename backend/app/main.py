from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging_config import SafeLogger
from app.ingestion.catalogue_loader import catalogue_loader
from app.ingestion.policy_loader import policy_loader
from app.retrieval.semantic_search import local_vector_index
from app.api.health import router as health_router
from app.api.catalogue import router as catalogue_router
from app.api.chat import router as chat_router
from app.api.evaluation import router as evaluation_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    SafeLogger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} for {settings.TEAM_NAME}")
    # 1. Load available catalogue
    catalogue_loader.load_default_catalogue()
    # 2. Load available policy
    policy_loader.load_default_policy()
    # 3. Build/load vector index
    if catalogue_loader.is_ready:
        local_vector_index.build_index()
    yield
    SafeLogger.info("Shutting down TruthCart AI application.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=f"{settings.TAGLINE} | Team {settings.TEAM_NAME} - Hackathon 2026",
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS middleware for configured frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Global safe error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    SafeLogger.error(f"Unhandled exception on {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Request could not be processed safely."}
    )

# Register API routers under /api
app.include_router(health_router, prefix="/api")
app.include_router(catalogue_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(evaluation_router, prefix="/api")

@app.get("/")
def root():
    return {
        "project": settings.PROJECT_NAME,
        "team": settings.TEAM_NAME,
        "tagline": settings.TAGLINE,
        "track": settings.TRACK,
        "status": "operational",
        "documentation": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
