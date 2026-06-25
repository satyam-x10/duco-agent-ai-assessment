from services.audio import AudioBriefingService

_audio_briefing_service_instance = None


def get_audio_briefing_service() -> AudioBriefingService:
    """Dependency provider resolving the AudioBriefingService singleton."""
    global _audio_briefing_service_instance
    if _audio_briefing_service_instance is None:
        _audio_briefing_service_instance = AudioBriefingService()
    return _audio_briefing_service_instance
