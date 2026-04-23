import uuid
import os
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.models.schemas import UploadResponse
from app.services.exif_metadata import extract_exif_metadata
from app.services.file_parser import (
    parse_file_with_diagnostics,
    SUPPORTED_EXTENSIONS,
    TEXT_EXTENSIONS,
    MEDIA_EXTENSIONS,
)
from app.store.memory_store import store, DocumentRecord

router = APIRouter()

DEFAULT_UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR = Path(os.environ.get("EXTRACTA_UPLOAD_DIR", str(DEFAULT_UPLOAD_DIR)))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _file_type(ext: str) -> str:
    if ext in TEXT_EXTENSIONS:
        if ext in {".jpg", ".jpeg", ".png"}:
            return "image"
        return "text"
    if ext in {".mp3", ".wav", ".m4a"}:
        return "audio"
    if ext in {".mp4", ".webm", ".mkv"}:
        return "video"
    return "text"


def _dated_upload_path(doc_id: str, ext: str) -> Path:
    now = datetime.now(timezone.utc)
    dated_dir = UPLOAD_DIR / f"{now.year:04d}" / f"{now.month:02d}" / f"{now.day:02d}"
    dated_dir.mkdir(parents=True, exist_ok=True)
    return dated_dir / f"{doc_id}{ext}"


@router.post("/upload", response_model=list[UploadResponse])
async def upload_files(files: list[UploadFile] = File(...)):
    results: list[UploadResponse] = []

    for file in files:
        ext = Path(file.filename or "").suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {ext}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
            )

        doc_id = str(uuid.uuid4())
        file_path = _dated_upload_path(doc_id, ext)

        content = await file.read()
        file_path.write_bytes(content)

        try:
            extraction = parse_file_with_diagnostics(file_path)
        except Exception as exc:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Failed to parse/transcribe '{file.filename}'. "
                    "For media files, ensure ffmpeg is installed and the server "
                    "did not restart during upload."
                ),
            ) from exc

        exif_meta = extract_exif_metadata(str(file_path))

        record = DocumentRecord(
            document_id=doc_id,
            filename=file.filename or "unknown",
            file_path=str(file_path),
            file_type=_file_type(ext),
            text=extraction.text,
            size=len(content),
            extraction_status=extraction.status,
            extraction_message=extraction.message,
            extractor_used=extraction.extractor_used,
            exif_metadata=exif_meta,
        )
        store.add_document(record)

        results.append(
            UploadResponse(
                document_id=doc_id,
                filename=record.filename,
                size=record.size,
                text_length=len(record.text),
                extraction_status=record.extraction_status,
                extraction_message=record.extraction_message,
                extractor_used=record.extractor_used,
                exif_metadata=exif_meta,
            )
        )

    return results
