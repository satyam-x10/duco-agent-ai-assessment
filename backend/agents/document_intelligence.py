import logging
from app.core.adk import Agent, SharedWorkflowState
from services.document_intelligence import DocumentIntelligenceService
from services.storage import StorageService

logger = logging.getLogger(__name__)


class DocIntelAgent(Agent):
    """Specialist agent coordinating document text extraction and OCR operations."""

    def __init__(self, doc_intel_service: DocumentIntelligenceService, storage_service: StorageService):
        super().__init__("DocIntelAgent")
        self.doc_intel_service = doc_intel_service
        self.storage_service = storage_service

    async def execute(self, state: SharedWorkflowState) -> None:
        logger.info(f"{self.name} parsing ready documents for claim {state.claim_id}")
        
        status = await self.storage_service.get_status()
        ready_types = [doc_type for doc_type, meta in status.items() if meta and meta.status == "ready"]
        
        for doc_type in ready_types:
            # Skip if already parsed in this workflow run
            if doc_type in state.processed_documents:
                continue
                
            file_path = await self.storage_service.get_file_path(doc_type)
            logger.info(f"{self.name} processing {doc_type.value} at {file_path}")
            
            # Execute parsing/OCR with dynamic strategy (e.g. high_fidelity on retry) using formal OCRTool
            strategy = state.ocr_strategies.get(doc_type, "standard")
            
            if state.mock_mode:
                import asyncio
                from app.schemas.document_intelligence import ProcessedDocument
                from app.schemas.intake import DocumentType
                
                await asyncio.sleep(0.8) # Simulate processing delay
                
                mock_texts = {
                    DocumentType.PRIYA_PT_INVOICE: "Priya Sen physical therapy invoice. Patient underwent physical therapy sessions. CPT code 97161 (Physical Therapy Evaluation, Billed: 20000.00) and CPT code 97110 (Therapeutic Exercises, Billed: 10000.00).",
                    DocumentType.AARAV_MRI_REPORT: "Aarav MRI report of lower extremity. Findings indicate tear of medial meniscus, ICD-10 diagnosis code M23.231. Procedure code CPT 73721 (MRI Joint Lower Extremity, Billed: 12000.00).",
                    DocumentType.SURGEON_ESTIMATE: "Surgeon Fee Estimate for Priya Sen. CPT code 29881 (Arthroscopic Meniscectomy, Billed: 100000.00) and CPT code 29888 (ACL reconstruction, Billed: 350000.00). Diagnosis: Tear of medial meniscus (ICD-10 M23.231).",
                    DocumentType.USER_QUERY_TRANSCRIPT: "Please coordinate benefits for patient Priya Sen, subscriber member ID 98765. She has primary insurance with BlueShield and secondary insurance with UnitedHealth."
                }
                extracted_text = mock_texts.get(doc_type, "Mock document text.")
                processed_doc = ProcessedDocument(
                    document_type=doc_type,
                    extracted_text=extracted_text,
                    page_count=1,
                    confidence=0.99,
                    metadata={
                        "parser": "MockProcessor",
                        "file_path": str(file_path),
                        "strategy": strategy,
                        "ocr_engine": "mock"
                    }
                )
            else:
                from tools.ocr_tool import OCRTool
                ocr_tool = OCRTool(self.doc_intel_service)
                processed_doc = await ocr_tool.run(file_path, doc_type, strategy=strategy, ocr_engine=state.ocr_engine)
            
            state.processed_documents[doc_type] = processed_doc
            
        logger.info(f"{self.name} completed parsing. {len(state.processed_documents)} documents now in state.")
