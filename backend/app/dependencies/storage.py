from app.config.settings import settings
from services.storage import StorageService, LocalStorageService, CloudStorageService


def get_storage_service() -> StorageService:
    """Dependency provider resolving the active storage engine based on settings."""
    if settings.STORAGE_TYPE == "gcs":
        return CloudStorageService()
    return LocalStorageService()
