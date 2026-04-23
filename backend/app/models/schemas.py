from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    size: int
    text_length: int
    extraction_status: str = "ok"
    extraction_message: str = ""
    extractor_used: str = ""
    exif_metadata: dict[str, Any] | None = None


class ProcessRequest(BaseModel):
    document_ids: list[str] = Field(default_factory=list)
    labels: list[str] | None = None
    confidence_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    enable_osint: bool = False
    osint_timeout_seconds: int = Field(default=20, ge=5, le=120)


class EntityPosition(BaseModel):
    start: int
    end: int


class HighlightRange(BaseModel):
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
    highlight_ranges: list[HighlightRange] = Field(default_factory=list)
    start: int | None = None
    end: int | None = None
    document_id: str
    document_name: str


class EvidenceOut(BaseModel):
    entity_id: str | None = None
    edge_key: str | None = None
    snippets: list[EvidenceSnippet]


class InvestigationFinding(BaseModel):
    title: str
    category: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    attributes: dict[str, Any] = Field(default_factory=dict)
    collected_at: str


class InvestigationOut(BaseModel):
    entity_id: str
    status: str = "not_requested"
    summary: str = ""
    findings: list[InvestigationFinding] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    variant: str | None = None


class InvestigationRunRequest(BaseModel):
    """Optional body for POST /entities/{id}/investigation/run."""

    source: Literal["tools", "instagram_leak"] = "tools"


class ProcessResponse(BaseModel):
    status: str
    entity_count: int
    edge_count: int
    document_ids: list[str]
    session_id: str | None = None


class ProcessStatusResponse(BaseModel):
    session_id: str
    status: str
    progress: int = 0
    total: int = 0
    current_file: str = ""
    entity_count: int = 0
    edge_count: int = 0
    documents_with_no_text: int = 0
    documents_skipped_for_extraction: int = 0
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None


class SessionOut(BaseModel):
    id: str
    name: str
    created_at: str | None = None
    document_count: int
    entity_count: int
    edge_count: int


class SessionDetail(SessionOut):
    documents: list[UploadResponse]


class BulkSessionDeleteRequest(BaseModel):
    session_ids: list[str] = Field(default_factory=list)


class BulkSessionDeleteOut(BaseModel):
    deleted_ids: list[str] = Field(default_factory=list)
    not_found_ids: list[str] = Field(default_factory=list)


class FaceOut(BaseModel):
    id: str
    document_id: str
    source_type: str
    source_ref: str
    bbox: list[float]
    confidence: float
    cluster_id: str
    thumbnail_path: str


class FaceClusterOut(BaseModel):
    cluster_id: str
    face_count: int
    document_count: int
    document_ids: list[str]
    document_names: dict[str, str]
    suggested_name: str | None = None
    display_name: str | None = None
    faces: list[FaceOut]


class FaceClusterNameUpdateRequest(BaseModel):
    display_name: str = ""


class FaceCompareRequest(BaseModel):
    face_id_a: str
    face_id_b: str
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)


class FaceCompareOut(BaseModel):
    face_id_a: str
    face_id_b: str
    similarity: float
    threshold: float
    match: bool
