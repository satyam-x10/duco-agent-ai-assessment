import logging
from app.core.adk import Agent, SharedWorkflowState
from app.schemas.intake import DocumentType
from app.schemas.medical_coding import CodingResult
from services.medical_coding import MedicalCodingService

logger = logging.getLogger(__name__)


class MedicalCodingAgent(Agent):
    """Specialist agent responsible for extracting CPT procedure and ICD-10 diagnosis codes from parsed documents."""

    def __init__(self, medical_coding_service: MedicalCodingService):
        super().__init__("MedicalCodingAgent")
        self.medical_coding_service = medical_coding_service

    async def execute(self, state: SharedWorkflowState) -> None:
        logger.info(f"{self.name} analyzing documents for claim {state.claim_id}")
        
        aggregated_result = CodingResult(diagnoses=[], procedures=[])
        
        # Check if we have previous warnings from the reviewer (reflection loop)
        reflection_warnings = None
        if state.warnings:
            reflection_warnings = [w for w in state.warnings if "confidence" in w.lower()]
            if reflection_warnings:
                logger.info(f"{self.name} detected active reflection warnings: {reflection_warnings}")
        
        # Analyze clinical files and aggregate coding results
        for doc_type, doc in state.processed_documents.items():
            # Skip user transcript query itself for medical coding, process clinical reports/invoices only
            if doc_type == DocumentType.USER_QUERY_TRANSCRIPT:
                continue
                
            logger.info(f"{self.name} executing medical coding on {doc_type.value}")
            from tools.coding_tool import MedicalCodingTool
            coding_tool = MedicalCodingTool(self.medical_coding_service)
            result = await coding_tool.run(doc, reflection_warnings=reflection_warnings)
            
            # Aggregate procedure and diagnosis lists
            aggregated_result.diagnoses.extend(result.diagnoses)
            aggregated_result.procedures.extend(result.procedures)
            
        # Deduplicate diagnoses (keep the one with the highest confidence)
        unique_diagnoses = {}
        for diag in aggregated_result.diagnoses:
            code = diag.code.strip().upper()
            if code not in unique_diagnoses or diag.confidence > unique_diagnoses[code].confidence:
                unique_diagnoses[code] = diag
        aggregated_result.diagnoses = list(unique_diagnoses.values())

        # Deduplicate procedures (keep the one with the highest confidence)
        unique_procedures = {}
        for proc in aggregated_result.procedures:
            code = proc.code.strip().upper()
            if code not in unique_procedures or proc.confidence > unique_procedures[code].confidence:
                unique_procedures[code] = proc
        aggregated_result.procedures = list(unique_procedures.values())
            
        state.coding_result = aggregated_result
        logger.info(
            f"{self.name} completed coding. Extracted {len(state.coding_result.procedures)} procedures "
            f"and {len(state.coding_result.diagnoses)} diagnoses."
        )
