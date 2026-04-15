import os

from fastapi import APIRouter, HTTPException

from app.models.schemas import UploadResponse
from app.store.memory_store import store

router = APIRouter()


@router.get("/documents", response_model=list[UploadResponse])
async def list_documents():
    docs = store.get_all_documents()
    return [
        UploadResponse(
            document_id=d.document_id,
            filename=d.filename,
            size=d.size,
            text_length=len(d.text),
        )
        for d in docs
    ]


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    doc = store.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError:
            pass

    store.delete_document(document_id)
    return {"status": "deleted", "document_id": document_id}
