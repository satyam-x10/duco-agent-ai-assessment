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
            engine_to_use = "library" if state.mock_mode else state.ocr_engine

            from tools.ocr_tool import OCRTool
            ocr_tool = OCRTool(self.doc_intel_service)
            processed_doc = await ocr_tool.run(file_path, doc_type, strategy=strategy, ocr_engine=engine_to_use)
            
            state.processed_documents[doc_type] = processed_doc
            
        logger.info(f"{self.name} completed parsing. {len(state.processed_documents)} documents now in state.")
