from pathlib import Path

import pytest

from agents.cob import COBAgent
from app.core.adk import FatalBusinessError, SharedWorkflowState
from app.schemas.document_intelligence import ProcessedDocument
from app.schemas.intake import DocumentType
from app.schemas.medical_coding import CodingResult, Diagnosis, Procedure
from services.cob_engine import COBEngine
from services.document_facts import extract_document_facts
from services.insurance_engine import InsuranceService


SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_inputs"


def _text_document(filename: str, document_type: DocumentType) -> ProcessedDocument:
    text = (SAMPLE_DIR / filename).read_text(encoding="utf-8")
    return ProcessedDocument(
        document_type=document_type,
        extracted_text=text,
        confidence=1.0,
        facts=extract_document_facts(text),
        metadata={"file_path": str(SAMPLE_DIR / filename), "parser": "TextProcessor"},
    )


def test_family_workflow_adjudicates_each_patient_under_their_own_member_id():
    insurance = InsuranceService()
    state = SharedWorkflowState(claim_id="FAMILY-1", member_id="UNRESOLVED")
    state.processed_documents = {
        DocumentType.PRIYA_PT_INVOICE: _text_document(
            "priya_pt_invoice_sample.txt", DocumentType.PRIYA_PT_INVOICE
        ),
        DocumentType.AARAV_MRI_REPORT: _text_document(
            "aarav_mri_report_sample.txt", DocumentType.AARAV_MRI_REPORT
        ),
        DocumentType.SURGEON_ESTIMATE: _text_document(
            "aarav_surgeon_estimate_sample.txt", DocumentType.SURGEON_ESTIMATE
        ),
    }
    state.coding_result = CodingResult(
        diagnoses=[
            Diagnosis(code="M54.50", description="Low back pain", confidence=1.0),
            Diagnosis(code="M23.231", description="Meniscus tear", confidence=1.0),
            Diagnosis(code="Z04.89", description="Normal ACL observation", confidence=1.0),
        ],
        procedures=[
            Procedure(code="97161", description="PT evaluation", confidence=1.0),
            Procedure(code="97110", description="Therapeutic exercise", confidence=1.0),
            Procedure(code="73721", description="Knee MRI", confidence=1.0),
            Procedure(code="29881", description="Meniscectomy", confidence=1.0),
            Procedure(code="29888", description="ACL reconstruction", confidence=1.0),
        ],
    )

    COBAgent(COBEngine(insurance)).coordinate_state(state)

    assert state.cob_decision is not None
    summaries = {summary.member_id: summary for summary in state.cob_decision.patient_claims}
    assert set(summaries) == {"98765", "98765-02"}
    assert summaries["98765"].patient_name == "Priya Sen"
    assert summaries["98765-02"].patient_name == "Aarav Sen"
    assert summaries["98765"].total_billed == 30000.0
    assert summaries["98765-02"].total_billed == 462000.0

    for line in state.cob_decision.lines_coverage:
        if line.cpt_code in {"97161", "97110"}:
            assert line.member_id == "98765"
            assert line.patient_name == "Priya Sen"
        else:
            assert line.member_id == "98765-02"
            assert line.patient_name == "Aarav Sen"

    acl_line = next(line for line in state.cob_decision.lines_coverage if line.cpt_code == "29888")
    assert acl_line.primary_coverage.is_covered is False
    assert "not medically necessary" in acl_line.remaining_balance.notes.lower()


def test_ungrounded_charge_is_rejected_instead_of_using_a_fixed_price():
    insurance = InsuranceService()
    text = "Patient Name: Priya Sen\nMember ID: 98765\nDiagnosis M54.50\nProcedure discussed: CPT 97161"
    state = SharedWorkflowState(
        claim_id="NO-PRICE",
        member_id="98765",
        processed_documents={
            DocumentType.PRIYA_PT_INVOICE: ProcessedDocument(
                document_type=DocumentType.PRIYA_PT_INVOICE,
                extracted_text=text,
                confidence=0.90,
                facts=extract_document_facts(text),
            )
        },
        coding_result=CodingResult(
            diagnoses=[Diagnosis(code="M54.50", description="Low back pain", confidence=1.0)],
            procedures=[Procedure(code="97161", description="PT evaluation", confidence=1.0)],
        ),
    )

    with pytest.raises(FatalBusinessError, match="refuses to substitute fixed prices"):
        COBAgent(COBEngine(insurance)).coordinate_state(state)


def test_member_accumulators_persist_deductible_and_oop_balances_across_claims():
    insurance = InsuranceService()
    engine = COBEngine(insurance)
    from app.schemas.cob_engine import Claim, ClaimLine

    first = engine.coordinate_benefits(
        Claim(
            claim_id="SEQ-1",
            member_id="98765",
            diagnoses=["M54.50"],
            lines=[ClaimLine(cpt_code="97161", billed_amount=20000.0)],
        )
    )
    second = engine.coordinate_benefits(
        Claim(
            claim_id="SEQ-2",
            member_id="98765",
            diagnoses=["M54.50"],
            lines=[ClaimLine(cpt_code="97110", billed_amount=10000.0)],
        )
    )

    assert first.lines_coverage[0].primary_coverage.deductible_applied == 20000.0
    assert second.lines_coverage[0].primary_coverage.deductible_applied == 0.0
    accumulator = insurance.get_accumulator(insurance._policies["BS-120-BLUE"], "98765")
    assert accumulator["remaining_individual_deductible"] == 0.0
    assert accumulator["remaining_out_of_pocket_max"] < 120000.0
