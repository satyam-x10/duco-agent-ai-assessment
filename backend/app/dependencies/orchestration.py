from app.dependencies.storage import get_storage_service
from app.dependencies.document_intelligence import get_doc_intel_service
from app.dependencies.medical_coding import get_medical_coding_service
from app.dependencies.insurance_engine import get_insurance_service
from app.dependencies.cob_engine import get_cob_engine
from app.dependencies.finance_engine import get_finance_service

from agents.intake import IntakeAgent
from agents.document_intelligence import DocIntelAgent
from agents.medical_coding import MedicalCodingAgent
from agents.insurance import InsuranceAgent
from agents.cob import COBAgent
from agents.finance import FinanceAgent
from agents.reviewer import ReviewerAgent
from app.core.adk import Orchestrator


def get_orchestrator() -> Orchestrator:
    """Dependency provider resolving the Orchestrator loaded with all specialist agents."""
    storage_service = get_storage_service()
    doc_intel_service = get_doc_intel_service()
    medical_coding_service = get_medical_coding_service()
    insurance_service = get_insurance_service()
    cob_engine = get_cob_engine()
    finance_engine = get_finance_service()

    intake_agent = IntakeAgent(storage_service)
    doc_intel_agent = DocIntelAgent(doc_intel_service, storage_service)
    medical_coding_agent = MedicalCodingAgent(medical_coding_service)
    insurance_agent = InsuranceAgent(insurance_service)
    cob_agent = COBAgent(cob_engine)
    finance_agent = FinanceAgent(finance_engine)
    reviewer_agent = ReviewerAgent()

    # The pipeline sequence of specialist agents
    agents = [
        intake_agent,
        doc_intel_agent,
        medical_coding_agent,
        insurance_agent,
        cob_agent,
        finance_agent,
        reviewer_agent,
    ]

    return Orchestrator(agents)
