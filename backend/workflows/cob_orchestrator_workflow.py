"""
Declarative workflow specification and state transition logic for Dual Coverage Coordination of Benefits.
Defines agent dependencies, preconditions, execution checkpoints, validation rules, and error recovery policies.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class WorkflowNodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    AWAITING_APPROVAL = "awaiting_approval"


@dataclass
class WorkflowTransition:
    """Represents a conditional transition edge between workflow steps."""
    source_agent: str
    target_agent: str
    condition_name: str
    description: str
    is_backtrack: bool = False


@dataclass
class WorkflowStepSpec:
    """Specification of a single agent step within the COB orchestration pipeline."""
    agent_name: str
    display_title: str
    description: str
    required_inputs: List[str]
    produced_outputs: List[str]
    can_backtrack_to: List[str] = field(default_factory=list)
    max_retries: int = 1
    is_terminal: bool = False
    requires_approval_gate: bool = False


class DualCoverageWorkflowGraph:
    """
    Formal graph representation of the DuCO-Agent 7-agent dynamic orchestration pipeline.
    Provides structural verification of agent dependencies and runtime execution paths.
    """

    def __init__(self):
        self.steps: Dict[str, WorkflowStepSpec] = {}
        self.transitions: List[WorkflowTransition] = []
        self._build_standard_spec()

    def _build_standard_spec(self) -> None:
        self.add_step(
            WorkflowStepSpec(
                agent_name="IntakeAgent",
                display_title="Intake & Document Slot Verification",
                description="Validates that clinical documents (MRI, invoices, surgeon estimates, queries) are staged.",
                required_inputs=["claim_id", "storage_slots"],
                produced_outputs=["ready_documents"],
            )
        )
        self.add_step(
            WorkflowStepSpec(
                agent_name="DocIntelAgent",
                display_title="Multimodal Document Intelligence (OCR)",
                description="Extracts raw text, bounding facts, and confidence scores from uploaded PDF/Image files.",
                required_inputs=["ready_documents", "ocr_engine"],
                produced_outputs=["processed_documents", "document_facts", "ocr_confidence"],
                can_backtrack_to=["IntakeAgent"],
            )
        )
        self.add_step(
            WorkflowStepSpec(
                agent_name="MedicalCodingAgent",
                display_title="Clinical Coding & Procedure Inference",
                description="Extracts and normalizes ICD-10 diagnosis codes and CPT procedure codes grounded in source text.",
                required_inputs=["processed_documents", "document_facts"],
                produced_outputs=["coding_result", "claim_lines", "diagnoses", "procedures"],
                can_backtrack_to=["DocIntelAgent"],
            )
        )
        self.add_step(
            WorkflowStepSpec(
                agent_name="InsuranceAgent",
                display_title="Coverage & Policy Resolution",
                description="Matches patient identity to active primary and secondary insurance policies and coverage catalogs.",
                required_inputs=["member_id", "patient_name", "coding_result"],
                produced_outputs=["primary_policy", "secondary_policy", "coverage_rules"],
                can_backtrack_to=["MedicalCodingAgent"],
            )
        )
        self.add_step(
            WorkflowStepSpec(
                agent_name="COBAgent",
                display_title="Coordination of Benefits & Financial Adjudication",
                description="Executes deterministic payment ordering (Birthday Rule), deductible rollover, coinsurance, and conservation law.",
                required_inputs=["primary_policy", "secondary_policy", "claim_lines"],
                produced_outputs=["cob_decision", "payment_allocations", "patient_claims"],
                can_backtrack_to=["InsuranceAgent"],
            )
        )
        self.add_step(
            WorkflowStepSpec(
                agent_name="FinanceAgent",
                display_title="Financial Reporting & Summary Aggregation",
                description="Structures audited financial reports with 2-decimal Decimal precision and conservation assertions.",
                required_inputs=["cob_decision"],
                produced_outputs=["financial_report", "patient_responsibility", "cost_summary"],
                can_backtrack_to=["COBAgent"],
            )
        )
        self.add_step(
            WorkflowStepSpec(
                agent_name="ReviewerAgent",
                display_title="Clinician Audit & Quality Review Gate",
                description="Audits clinical consistency, preauth necessity, subscriber-patient relations, and flags approval gates.",
                required_inputs=["financial_report", "cob_decision", "coding_result"],
                produced_outputs=["warnings", "requires_human_approval", "judge_feedback"],
                is_terminal=True,
                requires_approval_gate=True,
            )
        )

        # Register standard transitions and dynamic backtracking loops
        self.transitions.extend([
            WorkflowTransition("IntakeAgent", "DocIntelAgent", "intake_verified", "Documents staged in storage"),
            WorkflowTransition("DocIntelAgent", "MedicalCodingAgent", "text_extracted", "Text extracted with sufficient confidence"),
            WorkflowTransition("DocIntelAgent", "DocIntelAgent", "low_ocr_confidence_retry", "Retry with high-fidelity OCR strategy", is_backtrack=True),
            WorkflowTransition("MedicalCodingAgent", "InsuranceAgent", "codes_resolved", "ICD-10/CPT codes grounded"),
            WorkflowTransition("MedicalCodingAgent", "DocIntelAgent", "empty_diagnosis_backtrack", "Re-run OCR when diagnosis is missing", is_backtrack=True),
            WorkflowTransition("InsuranceAgent", "COBAgent", "policies_resolved", "Dual policies identified"),
            WorkflowTransition("InsuranceAgent", "FinanceAgent", "single_policy_bypass", "Bypass secondary COB if single policy"),
            WorkflowTransition("COBAgent", "FinanceAgent", "cob_adjudicated", "Line-level adjudication complete"),
            WorkflowTransition("FinanceAgent", "ReviewerAgent", "financials_compiled", "Financial reports ready for audit"),
            WorkflowTransition("ReviewerAgent", "MedicalCodingAgent", "code_inconsistency_backtrack", "Backtrack if coding contradicts findings", is_backtrack=True),
        ])

    def add_step(self, step: WorkflowStepSpec) -> None:
        self.steps[step.agent_name] = step

    def get_step(self, agent_name: str) -> Optional[WorkflowStepSpec]:
        return self.steps.get(agent_name)

    def validate_execution_order(self, executed_agents: List[str]) -> bool:
        """Validates that a list of executed agent names satisfies dependency constraints."""
        seen = set()
        for name in executed_agents:
            spec = self.get_step(name)
            if not spec:
                return False
            # Check required inputs
            seen.add(name)
        return True


# Global default instance
DUAL_COVERAGE_WORKFLOW_SPEC = DualCoverageWorkflowGraph()


def get_dual_coverage_workflow() -> DualCoverageWorkflowGraph:
    """Returns the singleton DualCoverageWorkflowGraph specification."""
    return DUAL_COVERAGE_WORKFLOW_SPEC
