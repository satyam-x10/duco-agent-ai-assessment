from datetime import datetime
from fastapi import APIRouter, File, Form, UploadFile, status, HTTPException
from app.schemas.intake import (
    DocumentType,
    DocumentMetadata,
    IntakeUploadResponse,
    IntakeStatusResponse,
    IntakeDeleteResponse,
)

router = APIRouter()

# In-memory database mock representing uploaded document metadata state
mock_intake_db = {
    DocumentType.PRIYA_PT_INVOICE: None,
    DocumentType.AARAV_MRI_REPORT: None,
    DocumentType.SURGEON_ESTIMATE: None,
    DocumentType.USER_QUERY_TRANSCRIPT: None,
}


@router.post("/upload", response_model=IntakeUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(..., description="The document file to upload"),
    document_type: DocumentType = Form(..., description="The target requirement slot for the file"),
):
    """
    Fulfills a document requirement slot by uploading a file.
    Validates file formats and registers metadata in local state.
    """
    allowed_extensions = {
        DocumentType.PRIYA_PT_INVOICE: [".pdf", ".png", ".jpg", ".jpeg"],
        DocumentType.AARAV_MRI_REPORT: [".pdf", ".png", ".jpg", ".jpeg"],
        DocumentType.SURGEON_ESTIMATE: [".pdf", ".png", ".jpg", ".jpeg"],
        DocumentType.USER_QUERY_TRANSCRIPT: [".txt", ".pdf"],
    }
    
    filename = file.filename or "unknown"
    file_ext = "." + filename.split(".")[-1].lower() if "." in filename else ""
    if file_ext not in allowed_extensions[document_type]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension {file_ext} is not allowed for slot {document_type.value}."
        )
        
    metadata = DocumentMetadata(
        filename=filename,
        size_bytes=102400,  # Simulated bytes
        content_type=file.content_type or "application/octet-stream",
        upload_time=datetime.utcnow(),
        status="ready"
    )
    mock_intake_db[document_type] = metadata
    
    return IntakeUploadResponse(
        status="success",
        message=f"Document '{filename}' successfully satisfied slot '{document_type.value}'.",
        document_type=document_type,
        metadata=metadata
    )


@router.get("/status", response_model=IntakeStatusResponse)
async def get_intake_status():
    """
    Queries the completion state of the intake workspace.
    Lists each slot requirement showing uploaded file metadata or null.
    """
    return IntakeStatusResponse(status=mock_intake_db)


@router.delete("/{documentType}", response_model=IntakeDeleteResponse)
async def delete_document(documentType: DocumentType):
    """
    Clears the document assigned to the specified requirement slot.
    """
    if mock_intake_db[documentType] is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No document uploaded for slot '{documentType.value}'."
        )
        
    mock_intake_db[documentType] = None
    return IntakeDeleteResponse(
        status="success",
        message=f"Requirement slot '{documentType.value}' has been successfully cleared.",
        document_type=documentType
    )
