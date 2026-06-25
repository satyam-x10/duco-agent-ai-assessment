from services.insurance_engine import InsuranceService

_insurance_service_instance = None


def get_insurance_service() -> InsuranceService:
    """Dependency provider resolving the InsuranceService singleton."""
    global _insurance_service_instance
    if _insurance_service_instance is None:
        _insurance_service_instance = InsuranceService()
    return _insurance_service_instance
