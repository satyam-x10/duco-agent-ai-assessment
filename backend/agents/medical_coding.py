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
            diagnosis_descriptions = {
                "M54.50": "Low back pain, unspecified",
                "M23.231": "Derangement of posterior horn of medial meniscus, right knee",
                "S83.511A": "Sprain of anterior cruciate ligament of right knee",
                "Z04.89": "Encounter for examination and observation",
            }
            procedure_descriptions = {
                "97161": "Physical therapy evaluation, low complexity",
                "97110": "Therapeutic exercises",
                "73721": "MRI lower extremity joint without contrast",
                "29881": "Knee arthroscopy with meniscectomy",
                "29888": "Arthroscopically aided ACL reconstruction",
            }
            for doc_type, doc in state.processed_documents.items():
                # Skip user transcript query itself for medical coding, process clinical reports/invoices only
                if doc_type == DocumentType.USER_QUERY_TRANSCRIPT:
                    continue
                    
                logger.info("%s deterministically coding explicit facts in %s", self.name, doc_type.value)
                result = CodingResult(
                    diagnoses=[
                        Diagnosis(
                            code=code,
                            description=diagnosis_descriptions.get(code, "Diagnosis documented in source"),
                            confidence=1.0,
                        )
                        for code in doc.facts.diagnosis_codes
                    ],
                    procedures=[
                        Procedure(
                            code=line.cpt_code,
                            description=procedure_descriptions.get(line.cpt_code, "Procedure documented in source"),
                            confidence=1.0,
                        )
                        for line in doc.facts.line_items
                    ],
                )
                
                # Aggregate procedure and diagnosis lists
                aggregated_result.diagnoses.extend(result.diagnoses)
                aggregated_result.procedures.extend(result.procedures)
        else:
            if not self.medical_coding_service.api_key:
                # Explicit codes extracted deterministically from source text do
                # not require an LLM. Inference-only documents still fail
                # closed and ask for Gemini/clinical review.
                explicit_diagnoses = []
                explicit_procedures = []
                for doc_type, doc in state.processed_documents.items():
                    if doc_type == DocumentType.USER_QUERY_TRANSCRIPT:
                        continue
                    explicit_diagnoses.extend(
                        Diagnosis(code=code, description="Diagnosis documented in source", confidence=1.0)
                        for code in doc.facts.diagnosis_codes
                    )
                    explicit_procedures.extend(
                        Procedure(code=line.cpt_code, description="Procedure documented in source", confidence=1.0)
                        for line in doc.facts.line_items
                    )
                if explicit_diagnoses and explicit_procedures:
                    aggregated_result = CodingResult(
                        diagnoses=explicit_diagnoses,
                        procedures=explicit_procedures,
                    )
                else:
                    raise RuntimeError(
                        "Uploaded documents require clinical-code inference, but GEMINI_API_KEY is not configured. "
                        "The pipeline will not invent codes from fixed scenario data."
                    )
            else:
            # LIVE MODE: Concatenate all document contents with structural headers so Gemini can analyze them contextually.
                combined_text_parts = []
                for doc_type, doc in state.processed_documents.items():
                    if doc_type == DocumentType.USER_QUERY_TRANSCRIPT:
                        continue
                    combined_text_parts.append(f"--- DOCUMENT TYPE: {doc_type.value} ---\n{doc.extracted_text}\n")

                combined_text = "\n".join(combined_text_parts)
                combined_doc = ProcessedDocument(
                    document_type=DocumentType.AARAV_MRI_REPORT,
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
