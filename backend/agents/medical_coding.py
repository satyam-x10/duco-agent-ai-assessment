import logging
from app.core.adk import Agent, SharedWorkflowState
from app.schemas.intake import DocumentType
from app.schemas.document_intelligence import ProcessedDocument
from app.schemas.medical_coding import CodingResult, Diagnosis, Procedure
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
        if state.mock_mode:
            for doc_type, doc in state.processed_documents.items():
                # Skip user transcript query itself for medical coding, process clinical reports/invoices only
                if doc_type == DocumentType.USER_QUERY_TRANSCRIPT:
                    continue
                    
                logger.info(f"{self.name} executing medical coding on {doc_type.value} (Mock Mode)")
                import asyncio
                await asyncio.sleep(1.0) # Simulate processing delay
                
                # Check document type and reflection state to simulate coding outcomes
                if doc_type == DocumentType.PRIYA_PT_INVOICE:
                    result = CodingResult(
                        diagnoses=[Diagnosis(code="M23.231", description="Tear of medial meniscus", confidence=0.96)],
                        procedures=[
                            Procedure(code="97161", description="Physical therapy evaluation", confidence=0.98),
                            Procedure(code="97110", description="Therapeutic exercises", confidence=0.95)
                        ]
                    )
                elif doc_type == DocumentType.AARAV_MRI_REPORT:
                    is_normal = True
                    if doc and doc.extracted_text and "tear" in doc.extracted_text.lower():
                        is_normal = False
                    
                    if is_normal:
                        result = CodingResult(
                            diagnoses=[Diagnosis(code="Z04.89", description="Normal MRI of right knee", confidence=0.99)],
                            procedures=[Procedure(code="73721", description="MRI Joint Lower Extremity", confidence=0.97)]
                        )
                    else:
                        result = CodingResult(
                            diagnoses=[Diagnosis(code="M23.231", description="Tear of medial meniscus", confidence=0.96)],
                            procedures=[Procedure(code="73721", description="MRI Joint Lower Extremity", confidence=0.97)]
                        )
                elif doc_type == DocumentType.SURGEON_ESTIMATE:
                    is_normal = True
                    mri_doc = state.processed_documents.get(DocumentType.AARAV_MRI_REPORT)
                    if mri_doc and mri_doc.extracted_text and "tear" in mri_doc.extracted_text.lower():
                        is_normal = False
                    if not mri_doc:
                        is_normal = False
                        
                    is_reflection = reflection_warnings is not None and len(reflection_warnings) > 0
                    cpt_29881_confidence = 0.98 if is_reflection else 0.65
                    
                    if is_normal:
                        result = CodingResult(
                            diagnoses=[Diagnosis(code="Z04.89", description="Normal MRI of right knee", confidence=0.99)],
                            procedures=[
                                Procedure(code="29881", description="Arthroscopic Meniscectomy", confidence=cpt_29881_confidence),
                                Procedure(code="29888", description="ACL reconstruction", confidence=0.95)
                            ]
                        )
                    else:
                        result = CodingResult(
                            diagnoses=[Diagnosis(code="M23.231", description="Tear of medial meniscus", confidence=0.96)],
                            procedures=[
                                Procedure(code="29881", description="Arthroscopic Meniscectomy", confidence=cpt_29881_confidence),
                                Procedure(code="29888", description="ACL reconstruction", confidence=0.95)
                            ]
                        )
                else:
                    result = CodingResult(diagnoses=[], procedures=[])
                
                # Aggregate procedure and diagnosis lists
                aggregated_result.diagnoses.extend(result.diagnoses)
                aggregated_result.procedures.extend(result.procedures)
        else:
            # LIVE MODE: Concatenate all document contents with structural headers so Gemini can analyze them contextually.
            combined_text_parts = []
            for doc_type, doc in state.processed_documents.items():
                if doc_type == DocumentType.USER_QUERY_TRANSCRIPT:
                    continue
                combined_text_parts.append(f"--- DOCUMENT TYPE: {doc_type.value} ---\n{doc.extracted_text}\n")
            
            combined_text = "\n".join(combined_text_parts)
            combined_doc = ProcessedDocument(
                document_type=DocumentType.AARAV_MRI_REPORT, # placeholder
                extracted_text=combined_text,
                page_count=1,
                confidence=1.0,
                metadata={"parser": "CombinedProcessor"}
            )
            
            from tools.coding_tool import MedicalCodingTool
            coding_tool = MedicalCodingTool(self.medical_coding_service)
            aggregated_result = await coding_tool.run(combined_doc, reflection_warnings=reflection_warnings)

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
