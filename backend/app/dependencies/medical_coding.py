from services.medical_coding import MedicalCodingService


def get_medical_coding_service() -> MedicalCodingService:
    """Dependency provider resolving the MedicalCodingService."""
    return MedicalCodingService()
