from fastapi import APIRouter
from app.api.v1.endpoints import health, intake, analysis, reports, rules

api_router = APIRouter()

# Register endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(intake.router, prefix="/intake", tags=["Intake"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["Analysis"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(rules.router, prefix="/rules", tags=["Rules Database"])

