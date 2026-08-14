import os
import uuid
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import UploadFile

from app.config.settings import settings
from app.schemas.intake import DocumentType, DocumentMetadata

logger = logging.getLogger(__name__)

# Base directory of the backend package (c:\Projects\hcl\duco-agent-ai-assessment\backend)
BASE_DIR = Path(__file__).resolve().parent.parent


class StorageError(Exception):
    """Base exception class for all storage operations."""
    pass


class StorageValidationError(StorageError):
    """Exception raised for file validation failures (size, format)."""
    pass


class StorageNotFoundError(StorageError):
    """Exception raised when a requested file or slot metadata does not exist."""
    pass


class StorageService(ABC):
    """Abstract Base Class defining the API contract for document storage services."""

    @abstractmethod
    async def save_file(self, file: UploadFile, document_type: DocumentType) -> DocumentMetadata:
        """Saves an uploaded file to the storage provider and returns its metadata."""
        pass

    @abstractmethod
    async def delete_file(self, document_type: DocumentType) -> None:
        """Deletes a file associated with the document type and clears metadata."""
        pass

    @abstractmethod
    async def get_file_path(self, document_type: DocumentType) -> Path:
        """Retrieves the physical storage path or GCS URI for a given document type."""
        pass

    @abstractmethod
    async def get_status(self) -> Dict[DocumentType, Optional[DocumentMetadata]]:
        """Retrieves the list of requirement slots and their loaded metadata."""
        pass


# Global in-memory registry to track active file metadata across requests
_metadata_registry: Dict[DocumentType, Optional[DocumentMetadata]] = {
    DocumentType.PRIYA_PT_INVOICE: None,
    DocumentType.AARAV_MRI_REPORT: None,
    DocumentType.SURGEON_ESTIMATE: None,
    DocumentType.USER_QUERY_TRANSCRIPT: None,
}


class LocalStorageService(StorageService):
    """Concrete implementation of StorageService using the local filesystem."""

    def __init__(self):
        self.upload_dir = BASE_DIR / settings.UPLOAD_DIR
        # Define strict allowed extension rules per slot
        self.allowed_formats: Dict[DocumentType, List[str]] = {
            DocumentType.PRIYA_PT_INVOICE: [".pdf", ".png", ".jpg", ".jpeg"],
            DocumentType.AARAV_MRI_REPORT: [".pdf", ".png", ".jpg", ".jpeg"],
            DocumentType.SURGEON_ESTIMATE: [".pdf", ".png", ".jpg", ".jpeg"],
            DocumentType.USER_QUERY_TRANSCRIPT: [".txt", ".pdf"],
        }

    async def save_file(self, file: UploadFile, document_type: DocumentType) -> DocumentMetadata:
        # 1. Validate extension
        filename = file.filename or "unnamed_file"
        file_ext = Path(filename).suffix.lower()
        allowed_exts = self.allowed_formats.get(document_type, [])
        
        if file_ext not in allowed_exts:
            raise StorageValidationError(
                f"File extension {file_ext} is not allowed for slot '{document_type.value}'. "
                f"Supported: {', '.join(allowed_exts)}"
            )

        # 2. Validate file size (FastAPI/Starlette populates file.size when parsed)
        if file.size and file.size > settings.MAX_UPLOAD_SIZE:
            max_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
            raise StorageValidationError(
                f"File size exceeds the maximum limit of {max_mb:.1f}MB."
            )

        # Ensure upload folder exists
        os.makedirs(self.upload_dir, exist_ok=True)

        # 3. Create unique upload name to prevent collisions
        unique_id = uuid.uuid4().hex
        stored_filename = f"{document_type.value}_{unique_id}{file_ext}"
        storage_path = self.upload_dir / stored_filename

        # 4. Stream write file contents
        try:
            # Reset file pointer to beginning just in case
            await file.seek(0)
            
            # Read and write in chunks to avoid blowing up memory on larger files
            size_bytes = 0
            with open(storage_path, "wb") as buffer:
                while chunk := await file.read(1024 * 1024):  # 1MB chunk size
                    size_bytes += len(chunk)
                    # Double-check size validation if file.size was somehow None
                    if size_bytes > settings.MAX_UPLOAD_SIZE:
                        raise StorageValidationError("File size exceeds the allowed limit during stream write.")
                    buffer.write(chunk)
        except Exception as e:
            # Clean up partial file on write failure
            if storage_path.exists():
                os.remove(storage_path)
            if isinstance(e, StorageValidationError):
                raise
            logger.error(f"Failed to write file to local disk: {e}")
            raise StorageError(f"Failed to store file on disk: {str(e)}")

        # 5. Populate and registry metadata
        metadata = DocumentMetadata(
            filename=stored_filename,
            original_filename=file.filename or "unnamed_file",
            size_bytes=size_bytes,
            content_type=file.content_type or "application/octet-stream",
            upload_time=datetime.utcnow(),
            status="ready"
        )
        
        # If there's an existing file, clean it up first
        await self.delete_file(document_type, quiet=True)
        
        # Save metadata and reference paths
        _metadata_registry[document_type] = metadata
        logger.info(f"File stored successfully at {storage_path} for slot {document_type.value}")
        return metadata

    async def delete_file(self, document_type: DocumentType, quiet: bool = False) -> None:
        metadata = _metadata_registry.get(document_type)
        if metadata is None:
            if quiet:
                return
            raise StorageNotFoundError(f"No document uploaded for requirement slot '{document_type.value}'.")
            
        file_path = self.upload_dir / metadata.filename
        if file_path.exists():
            try:
                os.remove(file_path)
                logger.info(f"Deleted local file at {file_path}")
            except Exception as e:
                logger.error(f"Failed to remove file from disk: {e}")
                if not quiet:
                    raise StorageError(f"Failed to delete stored file: {str(e)}")
                    
        _metadata_registry[document_type] = None

    async def get_file_path(self, document_type: DocumentType) -> Path:
        metadata = _metadata_registry.get(document_type)
        if metadata is None:
            raise StorageNotFoundError(f"No document uploaded for requirement slot '{document_type.value}'.")
        return self.upload_dir / metadata.filename

    async def get_status(self) -> Dict[DocumentType, Optional[DocumentMetadata]]:
        return _metadata_registry


class CloudStorageService(StorageService):
    """Mock implementation demonstrating a future Google Cloud Storage (GCS) engine.

    Routes integrate using StorageService interface, which allows swapping between LocalStorageService
    and CloudStorageService purely via Dependency Injection config variables.
    """

    async def save_file(self, file: UploadFile, document_type: DocumentType) -> DocumentMetadata:
        logger.info(f"[GCS Mock] Uploading '{file.filename}' to gs://duco-agent-bucket/uploads/")
        metadata = DocumentMetadata(
            filename=f"gcs_{document_type.value}_{uuid.uuid4().hex}.pdf",
            original_filename=file.filename or "unnamed_file",
            size_bytes=452000,
            content_type=file.content_type or "application/pdf",
            upload_time=datetime.utcnow(),
            status="ready"
        )
        _metadata_registry[document_type] = metadata
        return metadata

    async def delete_file(self, document_type: DocumentType) -> None:
        metadata = _metadata_registry.get(document_type)
        if metadata is None:
            raise StorageNotFoundError(f"No GCS document found for slot '{document_type.value}'.")
        logger.info(f"[GCS Mock] Deleting gs://duco-agent-bucket/uploads/{metadata.filename}")
        _metadata_registry[document_type] = None

    async def get_file_path(self, document_type: DocumentType) -> Path:
        metadata = _metadata_registry.get(document_type)
        if metadata is None:
            raise StorageNotFoundError(f"No document uploaded for requirement slot '{document_type.value}'.")
        # In a cloud scenario, this might return a GCS URI (gs://...) or download temp file
        return Path(f"gs://duco-agent-bucket/uploads/{metadata.filename}")

    async def get_status(self) -> Dict[DocumentType, Optional[DocumentMetadata]]:
        return _metadata_registry
