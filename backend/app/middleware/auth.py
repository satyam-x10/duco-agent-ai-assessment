import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.config.settings import settings

logger = logging.getLogger(__name__)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware enforcing API key / Token authentication on API endpoints.
    Allows public health checks and OpenAPI docs in development.
    """

    PUBLIC_PATHS = {"/", "/docs", "/openapi.json", "/redoc", f"{settings.API_V1_STR}/health"}

    async def dispatch(self, request: Request, call_next):
        if not settings.AUTH_ENABLED:
            return await call_next(request)

        path = request.url.path
        if path in self.PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        # Check X-API-Key header or Authorization Bearer header
        api_key = request.headers.get("X-API-Key")
        auth_header = request.headers.get("Authorization")

        if auth_header and auth_header.startswith("Bearer "):
            api_key = auth_header.split("Bearer ")[1].strip()

        if not api_key or api_key != settings.API_AUTH_KEY:
            logger.warning(f"Unauthorized API request blocked to {path}")
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Unauthorized: Invalid or missing API key. Provide a valid 'X-API-Key' or 'Authorization: Bearer' header."
                },
            )

        return await call_next(request)
