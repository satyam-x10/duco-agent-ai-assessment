from fastapi import APIRouter
from app.config.settings import settings
from app.schemas.health import HealthSchema

router = APIRouter()


@router.get("", response_model=HealthSchema)
async def get_health() -> HealthSchema:
    """Returns application health checks and configuration versions."""
    return HealthSchema(
        status="healthy",
        service="DuCO-Agent Backend",
        version=settings.VERSION
    )
