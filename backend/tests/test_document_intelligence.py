import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from app.schemas.intake import DocumentType
from services.document_intelligence import (
    DocumentProcessorFactory,
    DocumentIntelligenceService,
    TextProcessor,
    PDFProcessor,
    ImageProcessor,
)


@pytest.fixture
def doc_intel_service():
    """Fixture initializing a clean DocumentIntelligenceService."""
    factory = DocumentProcessorFactory()
    return DocumentIntelligenceService(factory=factory)


@pytest.mark.asyncio
async def test_text_processor():
    processor = TextProcessor()
    
    # Create temporary text file
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w+", delete=False, encoding="utf-8") as tmp:
        tmp.write("Priya Patel transcript query content")
        tmp_path = Path(tmp.name)
        
    try:
        processed = await processor.process(tmp_path, DocumentType.USER_QUERY_TRANSCRIPT)
        assert processed.extracted_text == "Priya Patel transcript query content"
        assert processed.page_count == 1
        assert processed.confidence == 1.0
        assert processed.metadata["parser"] == "TextProcessor"
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@pytest.mark.asyncio
@patch("services.document_intelligence.PdfReader")
async def test_pdf_processor_with_extractable_text(mock_pdf_reader):
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Peak Physical Therapy billing details CPT 97110"
    mock_pdf_reader.return_value.pages = [mock_page]
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", mode="wb", delete=False) as tmp:
        tmp.write(b"%PDF-1.4 mock content")
        tmp_path = Path(tmp.name)
        
    try:
        processor = PDFProcessor()
        processed = await processor.process(tmp_path, DocumentType.PRIYA_PT_INVOICE)
        
        assert "Peak Physical Therapy" in processed.extracted_text
        assert processed.page_count == 1
        assert processed.confidence == 0.99
        assert processed.metadata["parser"] == "PDFProcessor"
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@pytest.mark.asyncio
@patch("services.document_intelligence.PdfReader")
@patch("services.document_intelligence.genai.Client")
async def test_pdf_processor_scanned_fallback(mock_client_class, mock_pdf_reader, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key")
    
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "" # No extractable text
    mock_pdf_reader.return_value.pages = [mock_page]
    
    mock_response = MagicMock()
    mock_response.text = "Scanned PDF extracted content via Gemini OCR"
    
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", mode="wb", delete=False) as tmp:
        tmp.write(b"%PDF-1.4 mock content")
        tmp_path = Path(tmp.name)
        
    try:
        processor = PDFProcessor()
        processed = await processor.process(tmp_path, DocumentType.PRIYA_PT_INVOICE)
        
        assert processed.extracted_text == "Scanned PDF extracted content via Gemini OCR"
        assert processed.confidence == 0.90
        assert processed.metadata["parser"] == "PDFProcessor (Gemini OCR)"
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@pytest.mark.asyncio
@patch("services.document_intelligence.genai.Client")
async def test_image_processor_gemini(mock_client_class, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key")
    
    mock_response = MagicMock()
    mock_response.text = "Metro Imaging radiology report findings meniscus tear"
    
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client
    
    with tempfile.NamedTemporaryFile(suffix=".png", mode="w", delete=False) as tmp:
        tmp.write("")
        tmp_path = Path(tmp.name)
        
    try:
        processor = ImageProcessor()
        processed = await processor.process(tmp_path, DocumentType.AARAV_MRI_REPORT)
        
        assert "radiology report findings" in processed.extracted_text
        assert processed.confidence == 0.98
        assert processed.metadata["ocr_method"] == "GeminiVisionOCR"
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@pytest.mark.asyncio
async def test_image_processor_no_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    
    with tempfile.NamedTemporaryFile(suffix=".png", mode="w", delete=False) as tmp:
        tmp.write("")
        tmp_path = Path(tmp.name)
        
    try:
        processor = ImageProcessor()
        with pytest.raises(RuntimeError) as exc_info:
            await processor.process(tmp_path, DocumentType.AARAV_MRI_REPORT)
        assert "requires Gemini Vision OCR, but GEMINI_API_KEY is not configured" in str(exc_info.value)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def test_factory_resolutions():
    factory = DocumentProcessorFactory()
    
    assert isinstance(factory.get_processor(Path("doc.txt")), TextProcessor)
    assert isinstance(factory.get_processor(Path("doc.pdf")), PDFProcessor)
    assert isinstance(factory.get_processor(Path("doc.png")), ImageProcessor)
    assert isinstance(factory.get_processor(Path("doc.jpg")), ImageProcessor)
    assert isinstance(factory.get_processor(Path("doc.jpeg")), ImageProcessor)
    
    with pytest.raises(ValueError):
        factory.get_processor(Path("doc.docx"))


@pytest.mark.asyncio
async def test_service_file_not_found(doc_intel_service):
    non_existent_path = Path("non_existent_file.pdf")
    with pytest.raises(FileNotFoundError):
        await doc_intel_service.process_document(non_existent_path, DocumentType.SURGEON_ESTIMATE)

