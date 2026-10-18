import os
import io
import zipfile
import hashlib
import uuid
from abc import ABC, abstractmethod
from typing import Tuple, Optional
from fastapi import HTTPException, status
from app.core.config import settings


class StorageProvider(ABC):
    @abstractmethod
    def save(self, content: bytes, destination_key: str) -> str:
        """Save bytes to destination key and return the stored key."""
        pass

    @abstractmethod
    def get(self, storage_key: str) -> bytes:
        """Retrieve bytes from storage key."""
        pass

    @abstractmethod
    def delete(self, storage_key: str) -> bool:
        """Delete file associated with storage key."""
        pass

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Check if file exists."""
        pass


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = os.path.abspath(base_path or settings.LOCAL_STORAGE_PATH)
        os.makedirs(self.base_path, exist_ok=True)

    def _resolve_safe_path(self, storage_key: str) -> str:
        # Prevent path traversal attacks
        clean_key = os.path.normpath(storage_key).lstrip(r"\/")
        full_path = os.path.abspath(os.path.join(self.base_path, clean_key))
        try:
            if os.path.commonpath([self.base_path, full_path]) != self.base_path:
                raise ValueError("Path outside base directory")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security violation: Invalid storage path traversal detected.",
            )
        return full_path

    def save(self, content: bytes, destination_key: str) -> str:
        full_path = self._resolve_safe_path(destination_key)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        # Write safely
        temp_path = f"{full_path}.tmp"
        try:
            with open(temp_path, "wb") as f:
                f.write(content)
            if os.path.exists(full_path):
                os.remove(full_path)
            os.rename(temp_path, full_path)
        except Exception as e:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to securely persist file to local storage: {str(e)}",
            )
        return destination_key

    def get(self, storage_key: str) -> bytes:
        full_path = self._resolve_safe_path(storage_key)
        if not os.path.isfile(full_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found in storage.",
            )
        with open(full_path, "rb") as f:
            return f.read()

    def delete(self, storage_key: str) -> bool:
        try:
            full_path = self._resolve_safe_path(storage_key)
            if os.path.isfile(full_path):
                os.remove(full_path)
                return True
            return False
        except Exception:
            return False

    def exists(self, storage_key: str) -> bool:
        try:
            full_path = self._resolve_safe_path(storage_key)
            return os.path.isfile(full_path)
        except Exception:
            return False


class S3StorageProvider(StorageProvider):
    """
    S3 compatible object storage provider.
    Falls back gracefully to local storage if AWS credentials or boto3 are not configured.
    """
    def __init__(self):
        self._s3_client = None
        self._bucket = settings.S3_BUCKET
        if self._bucket:
            try:
                import boto3
                self._s3_client = boto3.client(
                    "s3",
                    endpoint_url=settings.S3_ENDPOINT_URL,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION,
                )
            except Exception:
                self._s3_client = None

        self._fallback_local = LocalStorageProvider()

    def save(self, content: bytes, destination_key: str) -> str:
        if self._s3_client and self._bucket:
            try:
                self._s3_client.put_object(
                    Bucket=self._bucket,
                    Key=destination_key,
                    Body=content,
                    ServerSideEncryption="AES256",
                )
                return destination_key
            except Exception:
                pass
        return self._fallback_local.save(content, destination_key)

    def get(self, storage_key: str) -> bytes:
        if self._s3_client and self._bucket:
            try:
                response = self._s3_client.get_object(
                    Bucket=self._bucket,
                    Key=storage_key,
                )
                return response["Body"].read()
            except Exception:
                pass
        return self._fallback_local.get(storage_key)

    def delete(self, storage_key: str) -> bool:
        if self._s3_client and self._bucket:
            try:
                self._s3_client.delete_object(
                    Bucket=self._bucket,
                    Key=storage_key,
                )
                return True
            except Exception:
                pass
        return self._fallback_local.delete(storage_key)

    def exists(self, storage_key: str) -> bool:
        if self._s3_client and self._bucket:
            try:
                self._s3_client.head_object(
                    Bucket=self._bucket,
                    Key=storage_key,
                )
                return True
            except Exception:
                return False
        return self._fallback_local.exists(storage_key)


def get_storage_provider() -> StorageProvider:
    if settings.STORAGE_TYPE.lower() == "s3" and settings.S3_BUCKET:
        return S3StorageProvider()
    return LocalStorageProvider()


# ==========================================
# File Validation & Utilities
# ==========================================

def calculate_sha256(content: bytes) -> str:
    """Calculate the hex-encoded SHA-256 hash of byte content."""
    return hashlib.sha256(content).hexdigest()


def validate_resume_file(content: bytes, original_filename: str) -> Tuple[str, str, str]:
    """
    Validates file signature (magic bytes), mime type, and file size.
    Returns: (detected_mime_type, file_extension, sha256_hash)
    Raises HTTPException on validation failures.
    """
    if not content or len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File '{original_filename}' is empty (0 bytes).",
        )

    if len(content) > settings.MAX_RESUME_FILE_SIZE_BYTES:
        max_mb = settings.MAX_RESUME_FILE_SIZE_BYTES // (1024 * 1024)
        status_413 = getattr(status, "HTTP_413_CONTENT_TOO_LARGE", None) or 413
        raise HTTPException(
            status_code=status_413,
            detail=f"File '{original_filename}' exceeds the maximum allowed size of {max_mb}MB.",
        )

    # 1. Check for PDF: starts with %PDF-
    if content.startswith(b"%PDF-"):
        mime_type = "application/pdf"
        ext = "pdf"
        sha256_hash = calculate_sha256(content)
        return mime_type, ext, sha256_hash

    # 2. Check for DOCX: starts with ZIP signature PK\x03\x04 and contains Word XML parts
    if content.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                # Security: ZIP decompression bomb mitigation
                MAX_ZIP_ENTRIES = 1000
                MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024  # 50 MB
                MAX_COMPRESSION_RATIO = 100

                infolist = zf.infolist()
                if len(infolist) > MAX_ZIP_ENTRIES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Security violation: Archive entry limit exceeded in '{original_filename}'.",
                    )

                total_uncompressed = 0
                for info in infolist:
                    total_uncompressed += info.file_size
                    if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Security violation: Decompressed archive size limit exceeded in '{original_filename}'.",
                        )
                    if info.compress_size > 0:
                        ratio = info.file_size / info.compress_size
                        if ratio > MAX_COMPRESSION_RATIO and info.file_size > 1024 * 1024:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Security violation: Anomalous compression ratio detected in '{original_filename}'.",
                            )

                namelist = zf.namelist()
                is_docx = any(name.startswith("word/") for name in namelist) or "[Content_Types].xml" in namelist
                if is_docx:
                    mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    ext = "docx"
                    sha256_hash = calculate_sha256(content)
                    return mime_type, ext, sha256_hash
        except HTTPException:
            raise
        except zipfile.BadZipFile:
            pass

    # Unsupported or corrupted
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(
            f"Unsupported or malformed file format for '{original_filename}'. "
            "Only valid PDF (.pdf) and Microsoft Word (.docx) documents are supported."
        ),
    )


def generate_storage_key(agency_id: uuid.UUID, file_extension: str) -> Tuple[str, str]:
    """
    Generates a secure server-side storage path and stored filename.
    Never uses the user's original filename to prevent path traversal and collisions.
    Returns: (storage_key, stored_filename)
    """
    file_id = uuid.uuid4().hex
    clean_ext = file_extension.lstrip(".").lower()
    stored_filename = f"{file_id}.{clean_ext}"
    storage_key = f"{str(agency_id)}/{stored_filename}"
    return storage_key, stored_filename
