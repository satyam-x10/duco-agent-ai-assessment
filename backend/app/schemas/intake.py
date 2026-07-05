from datetime import datetime
from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Supported required document slots in the DuCO-Agent platform."""
    PRIYA_PT_INVOICE = "priya_pt_invoice"
    AARAV_MRI_REPORT = "aarav_mri_report"
    SURGEON_ESTIMATE = "surgeon_estimate"
    USER_QUERY_TRANSCRIPT = "user_query_transcript"


class DocumentMetadata(BaseModel):
    """Metadata details representing a document stored in the workspace."""
    filename: str = Field(..., description="The name of the uploaded file")
    original_filename: Optional[str] = Field(None, description="The original name of the file uploaded by the user")
    size_bytes: int = Field(..., description="Size of the file in bytes")
    content_type: str = Field(..., description="MIME content type of the file")
    upload_time: datetime = Field(..., description="Timestamp when the file was uploaded")
    status: str = Field("ready", description="Current status of document parsing (ready / processing)")


class IntakeUploadResponse(BaseModel):
    """Response returned upon successful file upload into a requirement slot."""
    status: str = Field("success", description="Indicates if the upload was successful")
    message: str = Field(..., description="Detailed response status message")
    document_type: DocumentType = Field(..., description="The slot requirement this document satisfies")
    metadata: DocumentMetadata = Field(..., description="Uploaded document metadata details")


class IntakeStatusResponse(BaseModel):
    """Overall status layout of the intake workspace mapping the 4 slots."""
    status: Dict[DocumentType, Optional[DocumentMetadata]] = Field(
        ...,
        description="Dictionary mapping each DocumentType slot to its active document details, or null if missing"
    )


class IntakeDeleteResponse(BaseModel):
    """Response returned upon successful clearing of a document slot."""
    status: str = Field("success", description="Status code indicating outcome of deletion")
    message: str = Field(..., description="Detailed deletion response message")
    document_type: DocumentType = Field(..., description="The slot that was cleared")
