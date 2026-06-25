from services.preauth import PreAuthorizationService

_preauth_service_instance = None


def get_preauth_service() -> PreAuthorizationService:
    """Dependency provider resolving the PreAuthorizationService singleton."""
    global _preauth_service_instance
    if _preauth_service_instance is None:
        _preauth_service_instance = PreAuthorizationService()
    return _preauth_service_instance
