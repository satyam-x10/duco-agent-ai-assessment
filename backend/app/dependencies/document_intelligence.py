from services.document_intelligence import (
    DocumentProcessorFactory,
    DocumentIntelligenceService,
)

# Cached factory registry instance
_factory = DocumentProcessorFactory()


def get_doc_intel_service() -> DocumentIntelligenceService:
    """Dependency provider resolving the DocumentIntelligenceService."""
    return DocumentIntelligenceService(factory=_factory)
