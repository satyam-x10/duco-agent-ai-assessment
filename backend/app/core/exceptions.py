import logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from services.storage import StorageError, StorageValidationError, StorageNotFoundError

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Binds global API exception handlers to the FastAPI application instance."""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        logger.warning(f"HTTP exception on {request.url.path}: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "error_code": "HTTP_ERROR"
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Request validation failed",
                "errors": exc.errors(),
                "error_code": "VALIDATION_ERROR"
            },
        )

    @app.exception_handler(StorageValidationError)
    async def storage_validation_handler(request: Request, exc: StorageValidationError) -> JSONResponse:
        logger.warning(f"Storage validation failed on {request.url.path}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": str(exc),
                "error_code": "STORAGE_VALIDATION_ERROR"
            },
        )

    @app.exception_handler(StorageNotFoundError)
    async def storage_not_found_handler(request: Request, exc: StorageNotFoundError) -> JSONResponse:
        logger.warning(f"Storage resource not found on {request.url.path}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": str(exc),
                "error_code": "STORAGE_NOT_FOUND_ERROR"
            },
        )

    @app.exception_handler(StorageError)
    async def storage_general_handler(request: Request, exc: StorageError) -> JSONResponse:
        logger.error(f"Storage system error on {request.url.path}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Storage service error occurred.",
                "error_code": "STORAGE_SYSTEM_ERROR"
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(f"Unhandled exception on {request.url.path}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal server error occurred.",
                "error_code": "INTERNAL_SERVER_ERROR"
            },
        )
