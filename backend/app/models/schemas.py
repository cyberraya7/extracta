from __future__ import annotations

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    size: int
    text_length: int


class ProcessRequest(BaseModel):
    document_ids: list[str] = Field(default_factory=list)
    labels: list[str] | None = None
    confidence_threshold: float = Field(default=0.3, ge=0.0, le=1.0)


class EntityPosition(BaseModel):
    start: int
    end: int


class EntityOut(BaseModel):
    id: str
    text: str
    label: str
    score: float
    occurrences: int
    variants: list[str]
    positions: list[EntityPosition]


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    score: float
    occurrences: int
    connections: int


class GraphEdge(BaseModel):
    source: str
    target: str
    weight: float
    relationship: str
    source_label: str
    target_label: str


class GraphOut(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class EvidenceSnippet(BaseModel):
    text: str
    entity_text: str | None = None
    entities: list[str] | None = None
    start: int | None = None
    end: int | None = None
    document_id: str
    document_name: str


class EvidenceOut(BaseModel):
    entity_id: str | None = None
    edge_key: str | None = None
    snippets: list[EvidenceSnippet]


class ProcessResponse(BaseModel):
    status: str
    entity_count: int
    edge_count: int
    document_ids: list[str]
    session_id: str | None = None


class SessionOut(BaseModel):
    id: str
    name: str
    created_at: str | None = None
    document_count: int
    entity_count: int
    edge_count: int


class SessionDetail(SessionOut):
    documents: list[UploadResponse]
