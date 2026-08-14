from fastapi import APIRouter, File, Form, UploadFile, status, Depends
from app.schemas.intake import (
    DocumentType,
    IntakeUploadResponse,
    IntakeStatusResponse,
    IntakeDeleteResponse,
)
from app.dependencies.storage import get_storage_service
from services.storage import StorageService

router = APIRouter()


@router.post("/upload", response_model=IntakeUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(..., description="The document file to upload"),
    document_type: DocumentType = Form(..., description="The target requirement slot for the file"),
    storage_service: StorageService = Depends(get_storage_service),
):
    """
    Fulfills a document requirement slot by uploading a file.
    Validates file formats, file size, and stores it in the configured storage backend.
    """
    metadata = await storage_service.save_file(file, document_type)
    
    return IntakeUploadResponse(
        status="success",
        message=f"Document '{file.filename}' successfully satisfied slot '{document_type.value}'.",
        document_type=document_type,
        metadata=metadata
    )


@router.get("/status", response_model=IntakeStatusResponse)
async def get_intake_status(
    storage_service: StorageService = Depends(get_storage_service)
):
    """
    Queries the completion state of the intake workspace.
    Lists each slot requirement showing uploaded file metadata or null.
    """
    status_data = await storage_service.get_status()
    return IntakeStatusResponse(status=status_data)


@router.delete("/{documentType}", response_model=IntakeDeleteResponse)
async def delete_document(
    documentType: DocumentType,
    storage_service: StorageService = Depends(get_storage_service)
):
    """
    Clears the document assigned to the specified requirement slot and cleans up local storage.
    """
    await storage_service.delete_file(documentType)
    return IntakeDeleteResponse(
        status="success",
        message=f"Requirement slot '{documentType.value}' has been successfully cleared.",
        document_type=documentType
    )
