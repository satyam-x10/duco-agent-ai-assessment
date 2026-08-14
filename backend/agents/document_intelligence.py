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
                from services.document_facts import extract_document_facts
                
                await asyncio.sleep(0.8) # Simulate processing delay
                
                mock_texts = {
                    DocumentType.PRIYA_PT_INVOICE: "Patient Name: Priya Sen\nMember ID: 98765\nDiagnosis: M54.50\nCPT 97161 Physical Therapy Evaluation - INR 20000.00\nCPT 97110 Therapeutic Exercises - INR 10000.00\nTotal Billed: INR 30000.00",
                    DocumentType.AARAV_MRI_REPORT: "Patient Name: Aarav Sen\nMember ID: 98765-02\nMRI right knee CPT 73721 - INR 12000.00\nFindings: medial meniscus tear M23.231. ACL is intact with no tear.",
                    DocumentType.SURGEON_ESTIMATE: "Patient Name: Aarav Sen\nMember ID: 98765-02\nCPT 29881 Arthroscopic Meniscectomy - INR 100000.00\nCPT 29888 ACL reconstruction - INR 350000.00\nProposed pending MRI findings.",
                    DocumentType.USER_QUERY_TRANSCRIPT: "Patient: Priya Sen\nSubscriber ID: 98765\nPlease coordinate benefits under BlueShield and UnitedHealth."
                }
                extracted_text = mock_texts.get(doc_type, "Mock document text.")
                facts = extract_document_facts(extracted_text)
                processed_doc = ProcessedDocument(
                    document_type=doc_type,
                    extracted_text=extracted_text,
                    page_count=1,
                    confidence=0.99,
                    facts=facts,
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
