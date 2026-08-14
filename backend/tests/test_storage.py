import pytest
import io
import os
import shutil
from pathlib import Path
from fastapi import UploadFile

from app.config.settings import settings
from app.schemas.intake import DocumentType
from services.storage import (
    LocalStorageService,
    StorageValidationError,
    StorageNotFoundError,
)


@pytest.fixture(scope="function", autouse=True)
def setup_teardown_uploads_dir():
    """Fixture to override uploads path to a test directory and clean up after each run."""
    test_upload_dir = Path(__file__).resolve().parent.parent / "test_uploads"
    old_upload_dir = settings.UPLOAD_DIR
    settings.UPLOAD_DIR = "test_uploads"
    
    os.makedirs(test_upload_dir, exist_ok=True)
    yield
    # Clean up test uploads directory
    settings.UPLOAD_DIR = old_upload_dir
    if test_upload_dir.exists():
        shutil.rmtree(test_upload_dir)


@pytest.mark.asyncio
async def test_save_valid_file():
    service = LocalStorageService()
    
    # Create a mock text file for user_query_transcript which accepts .txt
    file_content = b"Priya Patel Coordination Query"
    mock_file = UploadFile(
        file=io.BytesIO(file_content),
        filename="query.txt",
        headers={"content-type": "text/plain"}
    )
    mock_file.size = len(file_content)

    metadata = await service.save_file(mock_file, DocumentType.USER_QUERY_TRANSCRIPT)
    
    assert metadata.filename.startswith("user_query_transcript_")
    assert metadata.original_filename == "query.txt"
    assert metadata.size_bytes == len(file_content)
    assert metadata.content_type == "text/plain"
    assert metadata.status == "ready"
    
    # Verify file is stored on disk
    file_path = await service.get_file_path(DocumentType.USER_QUERY_TRANSCRIPT)
    assert file_path.exists()
    assert file_path.read_bytes() == file_content


@pytest.mark.asyncio
async def test_save_invalid_extension():
    service = LocalStorageService()
    
    # user_query_transcript only accepts .txt and .pdf. Attempt .png upload
    mock_file = UploadFile(
        file=io.BytesIO(b"png_content_mock"),
        filename="image.png",
        headers={"content-type": "image/png"}
    )
    mock_file.size = 16
    
    with pytest.raises(StorageValidationError) as excinfo:
        await service.save_file(mock_file, DocumentType.USER_QUERY_TRANSCRIPT)
        
    assert "is not allowed for slot" in str(excinfo.value)


@pytest.mark.asyncio
async def test_save_file_exceeds_size_limit():
    service = LocalStorageService()
    
    # Temporarily set max size to 10 bytes
    old_max = settings.MAX_UPLOAD_SIZE
    settings.MAX_UPLOAD_SIZE = 10
    
    try:
        mock_file = UploadFile(
            file=io.BytesIO(b"larger than 10 bytes content"),
            filename="invoice.pdf",
            headers={"content-type": "application/pdf"}
        )
        mock_file.size = 28
        
        with pytest.raises(StorageValidationError) as excinfo:
            await service.save_file(mock_file, DocumentType.PRIYA_PT_INVOICE)
            
        assert "exceeds the maximum limit" in str(excinfo.value)
    finally:
        # Reset original limit
        settings.MAX_UPLOAD_SIZE = old_max


@pytest.mark.asyncio
async def test_delete_file():
    service = LocalStorageService()
    
    file_content = b"invoice contents"
    mock_file = UploadFile(
        file=io.BytesIO(file_content),
        filename="invoice.pdf",
        headers={"content-type": "application/pdf"}
    )
    mock_file.size = len(file_content)
    
    await service.save_file(mock_file, DocumentType.PRIYA_PT_INVOICE)
    file_path = await service.get_file_path(DocumentType.PRIYA_PT_INVOICE)
    assert file_path.exists()
    
    # Perform delete
    await service.delete_file(DocumentType.PRIYA_PT_INVOICE)
    assert not file_path.exists()
    
    # Verify metadata is cleared in status dictionary
    status_dict = await service.get_status()
    assert status_dict[DocumentType.PRIYA_PT_INVOICE] is None
    
    # Attempting to delete again should raise StorageNotFoundError
    with pytest.raises(StorageNotFoundError):
        await service.delete_file(DocumentType.PRIYA_PT_INVOICE)
