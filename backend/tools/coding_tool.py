import logging
from typing import List, Optional
from app.schemas.document_intelligence import ProcessedDocument
from app.schemas.medical_coding import CodingResult
from services.medical_coding import MedicalCodingService

logger = logging.getLogger(__name__)

class MedicalCodingTool:
    """Tool used by agents to infer CPT and ICD-10 medical codes using Gemini LLM inference."""
    
    def __init__(self, medical_coding_service: MedicalCodingService):
        self.name = "MedicalCodingTool"
        self.description = "Infers ICD-10 diagnoses and CPT procedure codes from clinical texts."
        self.medical_coding_service = medical_coding_service

    async def run(self, doc: ProcessedDocument, reflection_warnings: Optional[List[str]] = None) -> CodingResult:
        """Runs the Gemini medical coding inference logic on the document."""
        logger.info(f"[{self.name}] Inferring medical codes from document '{doc.document_type.value}'")
        return await self.medical_coding_service.analyze_document(
            doc=doc,
            reflection_warnings=reflection_warnings
        )
