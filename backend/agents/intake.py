import logging
from app.core.adk import Agent, SharedWorkflowState
from services.storage import StorageService

logger = logging.getLogger(__name__)


class IntakeAgent(Agent):
    """Specialist agent responsible for verifying document availability and validating intake status."""

    def __init__(self, storage_service: StorageService):
        super().__init__("IntakeAgent")
        self.storage_service = storage_service

    async def execute(self, state: SharedWorkflowState) -> None:
        logger.info(f"{self.name} validating intake status for claim {state.claim_id}")
        
        # Verify storage slots
        status = await self.storage_service.get_status()
        
        # Find which documents are loaded and ready
        ready_docs = {doc_type: meta for doc_type, meta in status.items() if meta and meta.status == "ready"}
        
        if not ready_docs:
            raise ValueError("No uploaded documents are present in storage slots. Intake verification failed.")
            
        logger.info(f"{self.name} verified {len(ready_docs)} ready documents in intake storage.")
