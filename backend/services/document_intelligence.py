import os
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict
from google import genai
from google.genai import types
from pypdf import PdfReader

from app.schemas.intake import DocumentType
from app.schemas.document_intelligence import ProcessedDocument

logger = logging.getLogger(__name__)


class DocumentProcessor(ABC):
    """Abstract class establishing the parsing contract for document processors."""

    @abstractmethod
    async def process(self, file_path: Path, document_type: DocumentType, strategy: str = "standard", ocr_engine: str = "gemini") -> ProcessedDocument:
        """Parses the document at file_path and constructs a structured ProcessedDocument."""
        pass


class TextProcessor(DocumentProcessor):
    """Concrete processor responsible for extracting raw unicode text files."""

    async def process(self, file_path: Path, document_type: DocumentType, strategy: str = "standard", ocr_engine: str = "gemini") -> ProcessedDocument:
        logger.info(f"TextProcessor reading file {file_path}")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read text file: {e}")
            raise IOError(f"Failed to parse text document: {str(e)}")

        if not content.strip():
            raise ValueError(f"Text document at '{file_path}' is empty.")

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
    """Concrete processor responsible for parsing PDF documents."""

    async def process(self, file_path: Path, document_type: DocumentType, strategy: str = "standard", ocr_engine: str = "gemini") -> ProcessedDocument:
        logger.info(f"PDFProcessor parsing PDF document {file_path} with strategy {strategy} and engine {ocr_engine}")

        try:
            reader = PdfReader(file_path)
            page_count = len(reader.pages)
            text_list = []
            for page in reader.pages:
                txt = page.extract_text()
                if txt:
                    text_list.append(txt)

            extracted_text = "\n".join(text_list)

            # Fall back to OCR if no text was found (scanned PDF) or if high-fidelity is requested
            if not extracted_text.strip() or strategy == "high_fidelity":
                logger.info(f"PDF {file_path.name} contains no extractable text or requested high-fidelity. OCR engine: {ocr_engine}.")
                if ocr_engine == "gemini":
                    extracted_text = await self._ocr_with_gemini(file_path, strategy=strategy)
                    parser_name = "PDFProcessor (Gemini OCR - High Fidelity)" if strategy == "high_fidelity" else "PDFProcessor (Gemini OCR)"
                else:
                    extracted_text = await self._ocr_with_rapidocr(file_path, strategy=strategy)
                    parser_name = "PDFProcessor (RapidOCR Local - High Fidelity)" if strategy == "high_fidelity" else "PDFProcessor (RapidOCR Local)"
                confidence = 0.99 if strategy == "high_fidelity" else 0.90
            else:
                confidence = 0.99
                parser_name = "PDFProcessor"

            return ProcessedDocument(
                document_type=document_type,
                extracted_text=extracted_text,
                page_count=page_count,
                confidence=confidence,
                metadata={
                    "parser": parser_name,
                    "page_count_resolved": page_count,
                    "file_path": str(file_path),
                    "strategy": strategy,
                    "ocr_engine": ocr_engine
                }
            )
        except (IOError, RuntimeError, ValueError):
            raise
        except Exception as e:
            logger.error(f"Failed to parse PDF document: {e}")
            raise IOError(f"Failed to parse PDF document '{file_path.name}': {str(e)}")

    async def _ocr_with_gemini(self, file_path: Path, strategy: str = "standard") -> str:
        """Performs Gemini Vision OCR on a scanned PDF. Raises on failure."""
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                f"Document '{file_path.name}' appears to be a scanned PDF requiring OCR, "
                "but GEMINI_API_KEY is not configured. Cannot extract text."
            )
        try:
            client = genai.Client(api_key=api_key)

            logger.info(f"[Gemini OCR] Calling Gemini Vision API on {file_path.name}")
            prompt = "Perform OCR on this scanned medical/estimate document. Return only the extracted text exactly as it appears. If it is handwritten or structured, extract it as accurately as possible."
            if strategy == "high_fidelity":
                prompt = (
                    "PERFORM DEEP OCR AUDIT AND EXTRACTION. Look extremely closely at all handwritten notes, structured tables, "
                    "mismatches, dates, insurance plan IDs, member names, and codes. Double check each digit and character. "
                    "Transcribe all text with highest possible fidelity, preserving the tabular structure where relevant."
                )
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_bytes(
                        data=file_path.read_bytes(),
                        mime_type="application/pdf",
                    ),
                    prompt
                ]
            )
            text = response.text
            if not text or not text.strip():
                raise RuntimeError(f"Gemini OCR returned empty response for '{file_path.name}'.")
            return text
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Gemini OCR failed for scanned PDF '{file_path.name}': {e}")
            raise RuntimeError(f"Gemini Vision OCR failed for '{file_path.name}': {str(e)}")

    async def _ocr_with_rapidocr(self, file_path: Path, strategy: str = "standard") -> str:
        """Performs local RapidOCR on a scanned PDF by extracting page images."""
        from pypdf import PdfReader
        from rapidocr_onnxruntime import RapidOCR
        
        logger.info(f"[RapidOCR PDF] Loading PDF from {file_path}")
        try:
            reader = PdfReader(file_path)
            engine = RapidOCR()
            texts = []
            
            for idx, page in enumerate(reader.pages):
                page_text = []
                # Try to extract embedded text first
                embedded = page.extract_text()
                if embedded and embedded.strip():
                    page_text.append(embedded)
                
                # Check for images on page to OCR
                if hasattr(page, "images") and page.images:
                    for img_idx, img in enumerate(page.images):
                        try:
                            res, elapse = engine(img.data)
                            if res:
                                page_text.append("\n".join([line[1] for line in res]))
                        except Exception as img_err:
                            logger.warning(f"Failed to OCR page {idx} image {img_idx} using local RapidOCR: {img_err}")
                
                if page_text:
                    texts.append("\n".join(page_text))
            
            return "\n\n".join(texts)
        except Exception as e:
            logger.error(f"Local RapidOCR failed for PDF '{file_path.name}': {e}")
            raise RuntimeError(f"Local OCR library failed for PDF '{file_path.name}': {str(e)}")


class ImageProcessor(DocumentProcessor):
    """Concrete processor parsing image formats. Uses Gemini Vision OCR API or Local RapidOCR."""

    async def process(self, file_path: Path, document_type: DocumentType, strategy: str = "standard", ocr_engine: str = "gemini") -> ProcessedDocument:
        logger.info(f"ImageProcessor executing OCR on image {file_path} with strategy {strategy} and engine {ocr_engine}")

        if ocr_engine == "gemini":
            extracted_text = await self._ocr_with_gemini(file_path, strategy=strategy)
            parser_name = "ImageProcessor"
            ocr_method = "GeminiVisionOCR (High Fidelity)" if strategy == "high_fidelity" else "GeminiVisionOCR"
        else:
            extracted_text = await self._ocr_with_rapidocr(file_path)
            parser_name = "ImageProcessor (RapidOCR Local)"
            ocr_method = "RapidOCRLocal"

        return ProcessedDocument(
            document_type=document_type,
            extracted_text=extracted_text,
            page_count=1,
            confidence=0.99 if strategy == "high_fidelity" else 0.98,
            metadata={
                "parser": parser_name,
                "ocr_method": ocr_method,
                "file_path": str(file_path),
                "strategy": strategy,
                "ocr_engine": ocr_engine
            }
        )

    async def _ocr_with_gemini(self, file_path: Path, strategy: str = "standard") -> str:
        """Performs Gemini Vision OCR on an image. Raises on failure."""
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                f"Image document '{file_path.name}' requires Gemini Vision OCR, "
                "but GEMINI_API_KEY is not configured. Cannot extract text."
            )

        ext = file_path.suffix.lower()
        mime_type = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"

        try:
            client = genai.Client(api_key=api_key)

            logger.info(f"[Gemini Vision OCR] Calling Gemini API on {file_path.name}")
            prompt = "Perform OCR on this medical/estimate document. Return only the extracted text exactly as it appears. If it is handwritten or structured, extract it as accurately as possible."
            if strategy == "high_fidelity":
                prompt = (
                    "PERFORM DEEP OCR AUDIT AND EXTRACTION. Look extremely closely at all handwritten notes, structured tables, "
                    "mismatches, dates, insurance plan IDs, member names, and codes. Double check each digit and character. "
                    "Transcribe all text with highest possible fidelity, preserving the tabular structure where relevant."
                )
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_bytes(
                        data=file_path.read_bytes(),
                        mime_type=mime_type,
                    ),
                    prompt
                ]
            )
            text = response.text
            if not text or not text.strip():
                raise RuntimeError(f"Gemini Vision OCR returned empty response for '{file_path.name}'.")
            return text
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Gemini Vision OCR API call failed for '{file_path.name}': {e}")
            raise RuntimeError(f"Gemini Vision OCR failed for '{file_path.name}': {str(e)}")

    async def _ocr_with_rapidocr(self, file_path: Path) -> str:
        """Performs local OCR on image using RapidOCR."""
        from rapidocr_onnxruntime import RapidOCR
        try:
            engine = RapidOCR()
            res, elapse = engine(str(file_path))
            if not res:
                raise ValueError("RapidOCR returned no text for this image.")
            return "\n".join([line[1] for line in res])
        except Exception as e:
            logger.error(f"Local RapidOCR failed for image '{file_path.name}': {e}")
            raise RuntimeError(f"Local OCR library failed for image '{file_path.name}': {str(e)}")


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

    async def process_document(self, file_path: Path, document_type: DocumentType, strategy: str = "standard", ocr_engine: str = "gemini") -> ProcessedDocument:
        if not file_path.exists():
            raise FileNotFoundError(f"Document file does not exist at path '{file_path}'.")

        processor = self.factory.get_processor(file_path)
        logger.info(f"Executing document intelligence pipeline on '{file_path.name}' for slot '{document_type.value}' with strategy '{strategy}' and OCR engine '{ocr_engine}'")
        return await processor.process(file_path, document_type, strategy=strategy, ocr_engine=ocr_engine)
