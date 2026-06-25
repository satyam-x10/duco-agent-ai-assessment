import pytest
import tempfile
from pathlib import Path
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
async def test_pdf_processor():
    processor = PDFProcessor()
    pdf_path = Path("mock_invoice.pdf")
    
    processed = await processor.process(pdf_path, DocumentType.PRIYA_PT_INVOICE)
    assert "Peak Physical Therapy" in processed.extracted_text
    assert "97110" in processed.extracted_text
    assert processed.page_count == 1
    assert processed.confidence == 0.99
    assert processed.metadata["parser"] == "PDFProcessor"


@pytest.mark.asyncio
async def test_image_processor():
    processor = ImageProcessor()
    img_path = Path("mock_mri.png")
    
    processed = await processor.process(img_path, DocumentType.AARAV_MRI_REPORT)
    assert "Metro Imaging" in processed.extracted_text
    assert "meniscus posterior horn tear" in processed.extracted_text.lower()
    assert processed.page_count == 1
    assert processed.confidence == 0.96
    assert processed.metadata["parser"] == "ImageProcessor"


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
