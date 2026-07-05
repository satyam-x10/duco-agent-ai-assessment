import logging
from pathlib import Path
from typing import Any, Dict
from app.schemas.intake import DocumentType
from app.schemas.document_intelligence import ProcessedDocument
from services.document_intelligence import DocumentIntelligenceService

logger = logging.getLogger(__name__)

class OCRTool:
    """Tool used by agents to perform OCR and text extraction on uploaded medical documents."""
    
    def __init__(self, doc_intel_service: DocumentIntelligenceService):
        self.name = "OCRTool"
        self.description = "Performs text extraction and OCR on medical reports, invoices, or query transcripts."
        self.doc_intel_service = doc_intel_service

    async def run(self, file_path: Any, document_type: DocumentType, strategy: str = "standard", ocr_engine: str = "gemini") -> ProcessedDocument:
        """Executes text processing or image OCR on the target file path."""
        path_obj = Path(file_path)
        logger.info(f"[{self.name}] Running OCR processing on '{path_obj.name}' (Strategy: {strategy}, Engine: {ocr_engine})")
        return await self.doc_intel_service.process_document(
            path_obj,
            document_type,
            strategy=strategy,
            ocr_engine=ocr_engine
        )
