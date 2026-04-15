import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.models.schemas import UploadResponse
from app.services.file_parser import parse_file, SUPPORTED_EXTENSIONS, TEXT_EXTENSIONS, MEDIA_EXTENSIONS
from app.store.memory_store import store, DocumentRecord

router = APIRouter()

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


def _file_type(ext: str) -> str:
    if ext in TEXT_EXTENSIONS:
        return "text"
    if ext in {".mp3", ".wav", ".m4a"}:
        return "audio"
    if ext in {".mp4", ".webm", ".mkv"}:
        return "video"
    return "text"


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
        file_path = UPLOAD_DIR / f"{doc_id}{ext}"

        content = await file.read()
        file_path.write_bytes(content)

        text = parse_file(file_path)

        record = DocumentRecord(
            document_id=doc_id,
            filename=file.filename or "unknown",
            file_path=str(file_path),
            file_type=_file_type(ext),
            text=text,
            size=len(content),
        )
        store.add_document(record)

        results.append(
            UploadResponse(
                document_id=doc_id,
                filename=record.filename,
                size=record.size,
                text_length=len(text),
            )
        )

    return results
