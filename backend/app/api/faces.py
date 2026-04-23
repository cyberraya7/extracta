from pathlib import Path

from fastapi.responses import FileResponse
from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    FaceOut,
    FaceClusterOut,
    FaceCompareRequest,
    FaceCompareOut,
    FaceClusterNameUpdateRequest,
)
from app.store.memory_store import store

router = APIRouter()


@router.get("/faces", response_model=list[FaceOut])
async def get_faces():
    return store.get_faces()


@router.get("/faces/{face_id}/similar", response_model=list[FaceOut])
async def get_similar_faces(face_id: str):
    rows = store.get_similar_faces(face_id)
    if not rows:
        raise HTTPException(status_code=404, detail="No similar faces found")
    return rows


@router.get("/faces/linked", response_model=list[FaceClusterOut])
async def get_linked_faces():
    return store.get_linked_faces()


@router.patch("/faces/linked/{cluster_id}/name")
async def update_face_cluster_name(cluster_id: str, payload: FaceClusterNameUpdateRequest):
    return store.set_face_cluster_display_name(cluster_id, payload.display_name)


@router.post("/faces/compare", response_model=FaceCompareOut)
async def compare_faces(payload: FaceCompareRequest):
    result = store.compare_faces(
        face_id_a=payload.face_id_a,
        face_id_b=payload.face_id_b,
        threshold=payload.threshold,
    )
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Unable to compare faces. Check face IDs and embeddings availability.",
        )
    return result


@router.get("/faces/thumbnail/{face_id}")
async def get_face_thumbnail(face_id: str):
    face = store.get_face(face_id)
    if not face or not face.get("thumbnail_path"):
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    path = Path(face["thumbnail_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail file not found")
    return FileResponse(path)
