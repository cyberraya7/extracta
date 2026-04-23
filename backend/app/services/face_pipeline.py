from __future__ import annotations

import io
import logging
import os
import uuid
import zipfile
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

_DEFAULT_FACE_SIM_THRESHOLD = 0.38

_face_analyzer = None


def _get_face_analyzer():
    global _face_analyzer
    if _face_analyzer is None:
        from insightface.app import FaceAnalysis

        _face_analyzer = FaceAnalysis(name="buffalo_l")
        _face_analyzer.prepare(ctx_id=-1, det_size=(640, 640))
        logger.info("InsightFace loaded")
    return _face_analyzer


def extract_faces_for_document(
    file_path: str,
    document_id: str,
    output_dir: Path,
) -> list[dict]:
    """Extract face detections and embeddings from a document file."""
    path = Path(file_path)
    ext = path.suffix.lower()
    images = _extract_document_images(path)
    if ext in {".jpg", ".jpeg", ".png"}:
        images.append({"source_type": "image", "source_ref": path.name, "image": _read_image(path)})

    detections: list[dict] = []
    for src in images:
        img = src["image"]
        if img is None:
            continue
        detections.extend(
            _detect_faces(
                img=img,
                source_type=src["source_type"],
                source_ref=src["source_ref"],
                document_id=document_id,
                output_dir=output_dir,
            )
        )
    return detections


def assign_face_clusters(
    face_instances: list[dict],
    threshold: float | None = None,
) -> None:
    """Assign cluster_id in-place using cosine similarity and union-find.

    Greedy single-pass clustering missed valid pairs depending on face order.
    Union-find merges every pair with similarity >= threshold (transitive closure).

    Override threshold with env ``EXTRACTA_FACE_SIMILARITY_THRESHOLD`` (0–1).
    """
    if threshold is None:
        threshold = float(
            os.environ.get(
                "EXTRACTA_FACE_SIMILARITY_THRESHOLD",
                str(_DEFAULT_FACE_SIM_THRESHOLD),
            )
        )
    n = len(face_instances)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        pi, pj = find(i), find(j)
        if pi != pj:
            parent[pi] = pj

    norms: list[np.ndarray | None] = []
    for inst in face_instances:
        emb = np.array(inst.get("embedding", []), dtype=np.float32)
        if emb.size == 0:
            norms.append(None)
            continue
        nrm = np.linalg.norm(emb)
        if nrm == 0:
            norms.append(None)
        else:
            norms.append(emb / nrm)

    for i in range(n):
        if norms[i] is None:
            continue
        for j in range(i + 1, n):
            if norms[j] is None:
                continue
            sim = float(np.dot(norms[i], norms[j]))
            if sim >= threshold:
                union(i, j)

    root_to_cluster: dict[int, str] = {}
    next_id = 0
    for i in range(n):
        root = find(i)
        if root not in root_to_cluster:
            root_to_cluster[root] = f"face_cluster_{next_id}"
            next_id += 1
        face_instances[i]["cluster_id"] = root_to_cluster[root]


def _extract_document_images(path: Path) -> list[dict]:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _extract_pdf_images(path)
    if ext == ".docx":
        return _extract_docx_images(path)
    return []


def _read_image(path: Path):
    try:
        from PIL import Image

        return np.array(Image.open(path).convert("RGB"))
    except Exception:
        logger.exception("Failed to read image %s", path)
        return None


def _extract_pdf_images(path: Path) -> list[dict]:
    images: list[dict] = []
    try:
        import fitz
        from PIL import Image
    except Exception:
        logger.warning("PyMuPDF/Pillow not available; skipping PDF face extraction")
        return images

    try:
        doc = fitz.open(str(path))
        for page_idx in range(len(doc)):
            page = doc.load_page(page_idx)
            for img_idx, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                base = doc.extract_image(xref)
                data = base.get("image")
                if not data:
                    continue
                arr = np.array(Image.open(io.BytesIO(data)).convert("RGB"))
                images.append(
                    {
                        "source_type": "pdf_image",
                        "source_ref": f"page_{page_idx+1}_img_{img_idx+1}",
                        "image": arr,
                    }
                )
        doc.close()
    except Exception:
        logger.exception("Failed extracting PDF images for %s", path)
    return images


def _extract_docx_images(path: Path) -> list[dict]:
    images: list[dict] = []
    try:
        from PIL import Image
    except Exception:
        logger.warning("Pillow not available; skipping DOCX face extraction")
        return images

    try:
        with zipfile.ZipFile(path, "r") as zf:
            media_files = [n for n in zf.namelist() if n.startswith("word/media/")]
            for idx, name in enumerate(media_files):
                data = zf.read(name)
                arr = np.array(Image.open(io.BytesIO(data)).convert("RGB"))
                images.append(
                    {
                        "source_type": "docx_image",
                        "source_ref": f"media_{idx+1}",
                        "image": arr,
                    }
                )
    except Exception:
        logger.exception("Failed extracting DOCX images for %s", path)
    return images


def _detect_faces(
    img: np.ndarray,
    source_type: str,
    source_ref: str,
    document_id: str,
    output_dir: Path,
) -> list[dict]:
    try:
        analyzer = _get_face_analyzer()
    except Exception:
        logger.warning("InsightFace not available; skipping face extraction")
        return []

    try:
        faces = analyzer.get(img)
    except Exception:
        logger.exception("Face detection failed for %s:%s", source_type, source_ref)
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    for i, face in enumerate(faces):
        bbox = [float(v) for v in face.bbox]
        emb = face.embedding.tolist() if hasattr(face, "embedding") else []
        face_id = f"face_{uuid.uuid4().hex[:16]}"
        thumb_path = output_dir / f"{face_id}.jpg"
        _save_thumbnail(img, bbox, thumb_path)
        results.append(
            {
                "id": face_id,
                "document_id": document_id,
                "source_type": source_type,
                "source_ref": source_ref,
                "bbox": bbox,
                "confidence": float(getattr(face, "det_score", 0.0)),
                "embedding": emb,
                "cluster_id": "",
                "thumbnail_path": str(thumb_path),
            }
        )
    return results


def _save_thumbnail(img: np.ndarray, bbox: list[float], out_path: Path) -> None:
    try:
        from PIL import Image

        x1, y1, x2, y2 = [int(v) for v in bbox]
        h, w = img.shape[:2]
        x1, x2 = max(0, x1), min(w, x2)
        y1, y2 = max(0, y1), min(h, y2)
        crop = img[y1:y2, x1:x2]
        if crop.size == 0:
            return
        Image.fromarray(crop).save(out_path)
    except Exception:
        logger.exception("Failed to save thumbnail %s", out_path)
