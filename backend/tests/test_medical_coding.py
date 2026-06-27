import pytest
import json
from unittest.mock import MagicMock, patch
from app.schemas.intake import DocumentType
from app.schemas.document_intelligence import ProcessedDocument
from app.schemas.medical_coding import CodingResult, Diagnosis, Procedure
from services.medical_coding import MedicalCodingService
from app.dependencies.medical_coding import get_medical_coding_service


@pytest.fixture
def clean_service():
    return MedicalCodingService()


@pytest.mark.asyncio
@patch("services.medical_coding.genai.Client")
async def test_medical_coding_gemini_success(mock_client_class, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "diagnoses": [
            {"code": "M23.231", "description": "Tear of medial meniscus", "confidence": 0.96}
        ],
        "procedures": [
            {"code": "29881", "description": "Arthroscopic Meniscectomy", "confidence": 0.98}
        ]
    })
    
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    service = MedicalCodingService()
    doc = ProcessedDocument(
        document_type=DocumentType.PRIYA_PT_INVOICE,
        extracted_text="Patient underwent arthroscopic meniscectomy of the right knee due to tear of medial meniscus.",
        page_count=1,
        confidence=0.99
    )
    
    res = await service.analyze_document(doc)
    assert len(res.diagnoses) == 1
    assert res.diagnoses[0].code == "M23.231"
    assert res.diagnoses[0].description == "Tear of medial meniscus"
    assert res.diagnoses[0].confidence == 0.96
    
    assert len(res.procedures) == 1
    assert res.procedures[0].code == "29881"
    assert res.procedures[0].description == "Arthroscopic Meniscectomy"
    assert res.procedures[0].confidence == 0.98
    
    # Verify all_codes unified property
    unified_codes = res.all_codes
    assert len(unified_codes) == 2
    assert unified_codes[0].code_type == "ICD-10"
    assert unified_codes[1].code_type == "CPT"


@pytest.mark.asyncio
@patch("services.medical_coding.genai.Client")
async def test_medical_coding_gemini_malformed_response(mock_client_class, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    
    # Return malformed/invalid JSON text
    mock_response = MagicMock()
    mock_response.text = "invalid json text payload"
    
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    service = MedicalCodingService()
    doc = ProcessedDocument(
        document_type=DocumentType.PRIYA_PT_INVOICE,
        extracted_text="Meniscus treatment",
        page_count=1,
        confidence=0.99
    )
    
    res = await service.analyze_document(doc)
    assert len(res.diagnoses) == 0
    assert len(res.procedures) == 0
    assert "Inference failure" in res.raw_response or "invalid json" in res.raw_response.lower()


@pytest.mark.asyncio
async def test_medical_coding_fallback_simulation(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    
    service = MedicalCodingService()
    doc = ProcessedDocument(
        document_type=DocumentType.SURGEON_ESTIMATE,
        extracted_text="Physical Therapy Evaluation with CPT 97161 and ACL reconstruction (cpt 29888). Patient has ACL tear.",
        page_count=2,
        confidence=0.99
    )
    
    res = await service.analyze_document(doc)
    assert len(res.diagnoses) > 0
    assert any(d.code == "S83.511A" for d in res.diagnoses)
    
    assert len(res.procedures) >= 2
    assert any(p.code == "97161" for p in res.procedures)
    assert any(p.code == "29888" for p in res.procedures)


def test_dependency_provider():
    service = get_medical_coding_service()
    assert isinstance(service, MedicalCodingService)
