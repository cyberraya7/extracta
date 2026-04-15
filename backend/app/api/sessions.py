from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.schemas import SessionOut, SessionDetail
from app.store.memory_store import store

router = APIRouter()


class RenameRequest(BaseModel):
    name: str


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions():
    return store.get_sessions()


@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session(session_id: str):
    info = store.get_session_info(session_id)
    if not info:
        raise HTTPException(status_code=404, detail="Session not found")
    return info


@router.post("/sessions/{session_id}/load")
async def load_session(session_id: str):
    if not store.load_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    info = store.get_session_info(session_id)
    return {"status": "loaded", "session": info}


@router.patch("/sessions/{session_id}")
async def rename_session(session_id: str, body: RenameRequest):
    if not store.rename_session(session_id, body.name):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "renamed", "session_id": session_id, "name": body.name}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    if not store.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted", "session_id": session_id}
