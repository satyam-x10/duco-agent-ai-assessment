import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List
from fastapi import status

from app.schemas.intake import DocumentType
from app.schemas.document_intelligence import ProcessedDocument

logger = logging.getLogger(__name__)


# High-fidelity mock text representations matching CPT codes and COB scenarios
MOCK_DOCUMENT_TEXTS = {
    DocumentType.PRIYA_PT_INVOICE: """
Peak Physical Therapy Clinic
Invoice ID: PT-2023-9981
Date: Oct 18, 2023
Patient Name: Priya Patel

Billing details:
Date       CPT Code  Description                         Units  Unit Cost  Total
2023-10-10 97110     Therapeutic Procedure (Exercise)    1      $150.00    $150.00
2023-10-12 97110     Therapeutic Procedure (Exercise)    1      $150.00    $150.00
2023-10-15 97110     Therapeutic Procedure (Exercise)    1      $150.00    $150.00
2023-10-10 97140     Manual Therapy Techniques           1      $100.00    $100.00
2023-10-12 97140     Manual Therapy Techniques           1      $100.00    $100.00

Total Billed: $650.00
Amount Paid: $0.00 (Pending insurance coordination)
""",
    DocumentType.AARAV_MRI_REPORT: """
Metro Imaging and Radiology Services
Report ID: RAD-MRI-8827
Date: Oct 20, 2023
Patient Name: Aarav Patel
Date of Birth: 2012-05-14

Procedure Code: CPT 73721 (MRI Lower Extremity Joint without contrast, Right Knee)

Clinical History: Knee pain following sports activity. Medial joint line tenderness.

Findings:
There is a complete vertical tear of the posterior horn of the medial meniscus.
Minimal joint effusion is present. The anterior cruciate ligament (ACL) and posterior
cruciate ligament (PCL) are intact. Collateral ligaments are normal.

Diagnosis: Complete medial meniscus posterior horn tear, right knee joint.
Total Facility Charge: $1200.00
""",
    DocumentType.SURGEON_ESTIMATE: """
Knee Specialist Clinic & Surgical Center
Surgical Estimate ID: EST-5527
Date: Oct 22, 2023
Patient Name: Aarav Patel
Date of Birth: 2012-05-14

Proposed Procedure: Right Knee Arthroscopy with Medial Meniscectomy
Procedure Code: CPT 29881 (Knee arthroscopy with meniscectomy)
Scheduled Date: Nov 15, 2023

Fee Schedule Estimates:
1. Surgeon Professional Fee (CPT 29881): $3200.00
2. Facility Operating Room Fee (Metro Surgical): $4500.00
3. Anesthesia Fee (Standard Pro-rata 2hr): $1200.00

Total Billed Estimate: $8900.00
Pre-authorization is required for CPT 29881.
""",
    DocumentType.USER_QUERY_TRANSCRIPT: """
Coordination of Benefits (COB) Query Transcript
Date: Oct 24, 2023
User Query:
"Hello, I am setting up the Coordination of Benefits for my family. My wife Priya Patel has dual coverage: she is the primary subscriber under BlueShield Cross (Group: BS120, Member: 98765) and she is also covered as a dependent under my secondary plan UnitedHealth (Group: UH990, Member: 12345).
Additionally, my son Aarav Patel is covered under both plans. I am the primary subscriber for Aarav under UnitedHealth (Group: UH990, Member: 12345), and he is a dependent under Priya's BlueShield Cross (Group: BS120, Member: 98765).
Priya recently completed physical therapy (billed amount $650.00) and Aarav has an upcoming knee meniscus surgery (surgeon estimate $8,900.00 and MRI facility cost $1,200.00).
Could you analyze these documents, determine which plan is primary for Priya and Aarav, calculate what each insurer is responsible to pay, and write the prior-authorization request letters?"
"""
}


class DocumentProcessor(ABC):
    """Abstract class establishing the parsing contract for document processors."""

    @abstractmethod
    async def process(self, file_path: Path, document_type: DocumentType) -> ProcessedDocument:
        """Parses the document at file_path and constructs a structured ProcessedDocument."""
        pass


class TextProcessor(DocumentProcessor):
    """Concrete processor responsible for extracting raw unicode text files."""

    async def process(self, file_path: Path, document_type: DocumentType) -> ProcessedDocument:
        logger.info(f"TextProcessor reading file {file_path}")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read text file: {e}")
            raise IOError(f"Failed to parse text document: {str(e)}")

        return ProcessedDocument(
            document_type=document_type,
            extracted_text=content,
            page_count=1,
            confidence=1.0,
            metadata={
                "parser": "TextProcessor",
                "character_count": len(content),
                "file_path": str(file_path)
            }
        )


class PDFProcessor(DocumentProcessor):
    """Concrete processor responsible for parsing PDF documents (using high-fidelity mocks)."""

    async def process(self, file_path: Path, document_type: DocumentType) -> ProcessedDocument:
        logger.info(f"PDFProcessor parsing PDF document {file_path}")
        
        # Simulate PDF reading. In future releases, this is where PyPDF or pdfplumber is called.
        mock_text = MOCK_DOCUMENT_TEXTS.get(
            document_type,
            f"Mock PDF text placeholder for document slot '{document_type.value}'."
        )

        return ProcessedDocument(
            document_type=document_type,
            extracted_text=mock_text,
            page_count=2 if document_type == DocumentType.SURGEON_ESTIMATE else 1,
            confidence=0.99,
            metadata={
                "parser": "PDFProcessor",
                "page_count_resolved": 2 if document_type == DocumentType.SURGEON_ESTIMATE else 1,
                "file_path": str(file_path)
            }
        )


class ImageProcessor(DocumentProcessor):
    """Concrete processor parsing image formats. Features Gemini Vision OCR hooks."""

    async def process(self, file_path: Path, document_type: DocumentType) -> ProcessedDocument:
        logger.info(f"ImageProcessor executing OCR on image {file_path}")
        
        # Call private Vision OCR hook
        extracted_text = await self._gemini_vision_ocr(file_path, document_type)

        return ProcessedDocument(
            document_type=document_type,
            extracted_text=extracted_text,
            page_count=1,
            confidence=0.96,
            metadata={
                "parser": "ImageProcessor",
                "ocr_method": "GeminiVisionMock",
                "file_path": str(file_path)
            }
        )

    async def _gemini_vision_ocr(self, file_path: Path, document_type: DocumentType) -> str:
        """Integration hook for Gemini Vision API. Swapped with actual model call in upcoming stages.

        Do NOT use actual Gemini SDK here as requested by constraints.
        """
        logger.info(f"[Gemini Vision Hook] Simulating OCR extraction on {file_path.name}")
        return MOCK_DOCUMENT_TEXTS.get(
            document_type,
            f"Mock OCR image text for slot '{document_type.value}'."
        )


class DocumentProcessorFactory:
    """Factory resolver mapping file extensions to specialized processors."""

    def __init__(self):
        self._processors: Dict[str, DocumentProcessor] = {
            ".txt": TextProcessor(),
            ".pdf": PDFProcessor(),
            ".png": ImageProcessor(),
            ".jpg": ImageProcessor(),
            ".jpeg": ImageProcessor(),
        }

    def get_processor(self, file_path: Path) -> DocumentProcessor:
        ext = file_path.suffix.lower()
        processor = self._processors.get(ext)
        if processor is None:
            raise ValueError(f"Unsupported file format extension: '{ext}'.")
        return processor


class DocumentIntelligenceService:
    """Coordinator service resolving processors and parsing documents into text schemas."""

    def __init__(self, factory: DocumentProcessorFactory):
        self.factory = factory

    async def process_document(self, file_path: Path, document_type: DocumentType) -> ProcessedDocument:
        if not file_path.exists():
            raise FileNotFoundError(f"Document file does not exist at path '{file_path}'.")
            
        processor = self.factory.get_processor(file_path)
        logger.info(f"Executing document intelligence pipeline on '{file_path.name}' for slot '{document_type.value}'")
        return await processor.process(file_path, document_type)
