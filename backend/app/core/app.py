from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.core.logging import setup_logging
from app.core.exceptions import register_exception_handlers
from app.api.v1.router import api_router


def get_app() -> FastAPI:
    """FastAPI application factory initializing core middlewares, exception handling, and routing."""
    # Configure standard logger
    setup_logging()
    
    # Instantiate app (enable openapi docs only in development environment)
    is_dev = settings.ENV == "development"
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url="/openapi.json" if is_dev else None,
        docs_url="/docs" if is_dev else None,
        redoc_url="/redoc" if is_dev else None,
    )
    
    # Resolve and register CORS origins
    origins = []
    if isinstance(settings.CORS_ORIGINS, list):
        origins = settings.CORS_ORIGINS
    elif isinstance(settings.CORS_ORIGINS, str):
        origins = [settings.CORS_ORIGINS]
        
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Bind global exception handlers
    register_exception_handlers(app)
    
    # Include versioned API routing
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    # Pre-populate sample documents if uploads folder is empty
    try:
        pre_populate_uploads()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to pre-populate sample files: {e}")
        
    return app


def pre_populate_uploads():
    """Automatically copies sample documents from /docs to /backend/uploads if empty."""
    import shutil
    from pathlib import Path
    
    base_dir = Path(__file__).resolve().parent.parent.parent.parent
    docs_dir = base_dir / "docs"
    uploads_dir = base_dir / "backend" / "uploads"
    
    if not uploads_dir.exists():
        uploads_dir.mkdir(parents=True, exist_ok=True)
        
    # Find any files other than .gitkeep
    existing = [f for f in uploads_dir.iterdir() if f.is_file() and f.name != ".gitkeep"]
    if not existing and docs_dir.exists():
        print(f"Pre-populating {uploads_dir} with sample documents...")
        for src_file in docs_dir.iterdir():
            if src_file.is_file() and src_file.name not in (".gitkeep", "test.py"):
                shutil.copy(src_file, uploads_dir / src_file.name)
                print(f"Auto-populated sample: {src_file.name}")
