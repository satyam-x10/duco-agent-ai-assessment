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
    
    return app
