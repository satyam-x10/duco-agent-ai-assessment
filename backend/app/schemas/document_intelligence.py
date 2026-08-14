from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.intake import DocumentType
from services.document_facts import DocumentFacts


class ProcessedDocument(BaseModel):
    """Unified validation schema representing the output of any document parser/OCR engine."""
    document_type: DocumentType = Field(..., description="The satisfied intake slot this text matches")
    extracted_text: str = Field(..., description="The raw OCR or parsed text content of the file")
    page_count: int = Field(1, description="Number of pages resolved in the document")
    confidence: float = Field(..., description="Confidence score of the parser (0.0 to 1.0)")
    facts: DocumentFacts = Field(default_factory=DocumentFacts, description="Extracted structured facts from OCR")
    quality_issues: List[str] = Field(default_factory=list, description="Quality issues or ungrounded artifacts identified")
    metadata: dict = Field(default_factory=dict, description="Additional document parameters (file paths, parsing speed)")
