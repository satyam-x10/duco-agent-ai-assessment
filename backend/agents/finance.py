import logging
from app.core.adk import Agent, SharedWorkflowState
from services.finance_engine import FinanceEngine

logger = logging.getLogger(__name__)


class FinanceAgent(Agent):
    """Specialist agent responsible for auditing financial balances and patient out-of-pocket splits."""

    def __init__(self, finance_engine: FinanceEngine):
        super().__init__("FinanceAgent")
        self.finance_engine = finance_engine

    async def execute(self, state: SharedWorkflowState) -> None:
        logger.info(f"{self.name} generating financial breakdown for claim {state.claim_id}")
        
        if not state.cob_decision:
            raise ValueError("No Coordination of Benefits decision is present. Finance adjudication cannot proceed.")
            
        # Execute financial report generation
        financial_report = self.finance_engine.generate_financial_breakdown(state.cob_decision)
        
        state.financial_report = financial_report
        logger.info(
            f"{self.name} generated report {financial_report.report_id}. "
            f"Patient total out-of-pocket obligation: ${financial_report.breakdown.summary.total_patient_responsibility:.2f}"
        )
