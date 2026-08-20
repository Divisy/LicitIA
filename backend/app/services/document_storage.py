"""Object storage for tender documents (local volume or Cloudflare R2)."""
from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Generator, Optional

from fastapi.responses import FileResponse, StreamingResponse
from starlette.responses import Response

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_CHUNK_SIZE = 64 * 1024


def normalize_object_key(object_key: str) -> str:
    """Normalize and validate a stored object key (relative path in bucket/volume)."""
    raw = object_key.strip()
    if raw.startswith("/") or "://" in raw:
        raise ValueError("Invalid document object key")
    key = raw.replace("\\", "/").lstrip("/")
    parts = [part for part in key.split("/") if part not in ("", ".")]
    if not parts or any(part == ".." for part in parts):
        raise ValueError("Invalid document object key")
    return "/".join(parts)


def is_r2_configured() -> bool:
    return all(
        [
            settings.R2_ACCOUNT_ID,
            settings.R2_ACCESS_KEY_ID,
            settings.R2_SECRET_ACCESS_KEY,
            settings.R2_BUCKET_NAME,
        ]
    )


def uses_r2_storage() -> bool:
    return settings.DOCUMENT_STORAGE_BACKEND.lower() == "r2" and is_r2_configured()


class DocumentStorageService:
    """Read/write tender document blobs from local disk and/or Cloudflare R2."""

    def __init__(self) -> None:
        self._local_root = Path(settings.DOCUMENTS_STORAGE_PATH).resolve()
        self._backend = settings.DOCUMENT_STORAGE_BACKEND.lower()
        self._write_local = settings.DOCUMENT_STORAGE_WRITE_LOCAL or self._backend != "r2"
        self._s3 = None

        if self._backend == "r2":
            if not is_r2_configured():
                raise RuntimeError(
                    "DOCUMENT_STORAGE_BACKEND=r2 but R2 credentials are incomplete"
                )
            self._s3 = self._create_r2_client()

    def _create_r2_client(self):
        import boto3
        from botocore.config import Config

        endpoint = settings.r2_endpoint_url
        return boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name=settings.R2_REGION,
            config=Config(signature_version="s3v4"),
        )

    def _bucket_key(self, object_key: str) -> str:
        key = normalize_object_key(object_key)
        prefix = (settings.R2_PREFIX or "").strip("/")
        return f"{prefix}/{key}" if prefix else key

    def local_path(self, object_key: str) -> Path:
        key = normalize_object_key(object_key)
        candidate = (self._local_root / key).resolve()
        if self._local_root not in candidate.parents and candidate != self._local_root:
            raise ValueError("Invalid document object key")
        return candidate

    def exists(self, object_key: str) -> bool:
        key = normalize_object_key(object_key)
        if self.local_path(key).is_file():
            return True
        if self._s3 is not None:
            try:
                self._s3.head_object(Bucket=settings.R2_BUCKET_NAME, Key=self._bucket_key(key))
                return True
            except Exception as exc:
                from botocore.exceptions import ClientError

                if isinstance(exc, ClientError) and exc.response.get("Error", {}).get("Code") == "404":
                    return False
                if isinstance(exc, ClientError):
                    logger.warning("R2 head_object failed for %s: %s", key, exc)
                    return False
                raise
        return False

    def persist_local_file(self, source_path: Path, object_key: str) -> str:
        """
        Persist a downloaded SECOP file under the configured backend(s).

        Returns the normalized object key stored in tender_documents.file_path.
        """
        key = normalize_object_key(object_key)
        source_path = source_path.resolve()

        if self._s3 is not None:
            if not source_path.is_file():
                raise FileNotFoundError(f"Source file not found: {source_path}")
            bucket_key = self._bucket_key(key)
            logger.info("Uploading document to R2: %s", bucket_key)
            self._s3.upload_file(
                str(source_path),
                settings.R2_BUCKET_NAME,
                bucket_key,
            )

        if not self._write_local and self._s3 is not None:
            if source_path.is_file():
                source_path.unlink(missing_ok=True)
        elif self._s3 is None and source_path != self.local_path(key):
            destination = self.local_path(key)
            destination.parent.mkdir(parents=True, exist_ok=True)
            source_path.replace(destination)

        return key

    def upload_local_copy(self, object_key: str) -> bool:
        """Upload an existing local file to R2 (migration helper)."""
        if self._s3 is None:
            return False
        local_file = self.local_path(object_key)
        if not local_file.is_file():
            return False
        bucket_key = self._bucket_key(object_key)
        self._s3.upload_file(
            str(local_file),
            settings.R2_BUCKET_NAME,
            bucket_key,
        )
        return True

    def iter_file_chunks(self, object_key: str) -> Generator[bytes, None, None]:
        key = normalize_object_key(object_key)
        local_file = self.local_path(key)
        if local_file.is_file():
            with local_file.open("rb") as handle:
                while True:
                    chunk = handle.read(_CHUNK_SIZE)
                    if not chunk:
                        break
                    yield chunk
            return

        if self._s3 is None:
            raise FileNotFoundError(key)

        response = self._s3.get_object(
            Bucket=settings.R2_BUCKET_NAME,
            Key=self._bucket_key(key),
        )
        body = response["Body"]
        try:
            while True:
                chunk = body.read(_CHUNK_SIZE)
                if not chunk:
                    break
                yield chunk
        finally:
            body.close()

    def build_download_response(self, object_key: str, file_name: str) -> Response:
        key = normalize_object_key(object_key)
        media_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        local_file = self.local_path(key)

        if local_file.is_file():
            return FileResponse(
                path=local_file,
                filename=file_name,
                media_type=media_type,
            )

        if self._s3 is None:
            raise FileNotFoundError(key)

        return StreamingResponse(
            self.iter_file_chunks(key),
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
        )

    def delete_object(self, object_key: str) -> None:
        """Remove a stored document blob from local disk and/or R2."""
        key = normalize_object_key(object_key)
        local_file = self.local_path(key)
        if local_file.is_file():
            local_file.unlink(missing_ok=True)

        if self._s3 is not None:
            try:
                self._s3.delete_object(
                    Bucket=settings.R2_BUCKET_NAME,
                    Key=self._bucket_key(key),
                )
            except Exception as exc:
                logger.warning("Failed to delete R2 object %s: %s", key, exc)


_storage_service: Optional[DocumentStorageService] = None


def get_document_storage() -> DocumentStorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = DocumentStorageService()
    return _storage_service
