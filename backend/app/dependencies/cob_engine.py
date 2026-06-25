from app.dependencies.insurance_engine import get_insurance_service
from services.cob_engine import COBEngine

_cob_engine_instance = None


def get_cob_engine() -> COBEngine:
    """Dependency provider resolving the COBEngine singleton."""
    global _cob_engine_instance
    if _cob_engine_instance is None:
        insurance_service = get_insurance_service()
        _cob_engine_instance = COBEngine(insurance_service)
    return _cob_engine_instance
