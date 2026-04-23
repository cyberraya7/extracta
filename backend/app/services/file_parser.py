import csv
import io
import logging
import os
from dataclasses import dataclass
from pathlib import Path

import pdfplumber
from docx import Document

from app.utils.text_utils import clean_text

logger = logging.getLogger(__name__)

TEXT_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv", ".jpg", ".jpeg", ".png"}
MEDIA_EXTENSIONS = {".mp3", ".wav", ".m4a", ".mp4", ".webm", ".mkv"}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | MEDIA_EXTENSIONS

_whisper_model = None
_paddle_ocr = None
_enable_pdf_ocr = os.environ.get("EXTRACTA_ENABLE_PDF_OCR", "1") == "1"


@dataclass
class ExtractionResult:
    text: str
    status: str
    message: str = ""
    extractor_used: str = ""


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        logger.info("Loading Whisper model (base)...")
        _whisper_model = whisper.load_model("base")
        logger.info("Whisper model loaded")
    return _whisper_model


def _get_paddle_ocr():
    global _paddle_ocr
    if _paddle_ocr is None:
        from paddleocr import PaddleOCR

        logger.info("Loading PaddleOCR model...")
        _paddle_ocr = PaddleOCR(use_angle_cls=True, lang="en")
        logger.info("PaddleOCR loaded")
    return _paddle_ocr


def parse_file(file_path: str | Path) -> str:
    """Backward-compatible text-only extraction helper."""
    return parse_file_with_diagnostics(file_path).text


def parse_file_with_diagnostics(file_path: str | Path) -> ExtractionResult:
    """Extract text and return diagnostics for UX and troubleshooting."""
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")
    if ext == ".pdf":
        return _extract_pdf_with_diagnostics(path)
    if ext in {".jpg", ".jpeg", ".png"}:
        return _extract_image_text_with_diagnostics(path)
    if ext in MEDIA_EXTENSIONS:
        return _extract_media_with_diagnostics(path)

    extractor = _EXTRACTORS[ext]
    raw = clean_text(extractor(path))
    if raw:
        return ExtractionResult(
            text=raw,
            status="ok",
            extractor_used=ext.lstrip("."),
        )
    return ExtractionResult(
        text="",
        status="empty_text",
        message="No extractable text found in file content.",
        extractor_used=ext.lstrip("."),
    )


def _extract_pdf_with_diagnostics(path: Path) -> ExtractionResult:
    pages: list[str] = []
    ocr_attempted = False
    ocr_success = False
    ocr_unavailable = False

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = (page.extract_text() or "").strip()
            if text:
                pages.append(text)
                continue
            if not _enable_pdf_ocr:
                continue
            ocr_attempted = True
            ocr_text, unavailable = _ocr_pdf_page(path, page.page_number - 1)
            ocr_unavailable = ocr_unavailable or unavailable
            if ocr_text:
                ocr_success = True
                pages.append(ocr_text)

    combined = clean_text("\n\n".join(pages))
    if combined:
        return ExtractionResult(
            text=combined,
            status="ok",
            extractor_used="pdfplumber+paddleocr" if ocr_attempted else "pdfplumber",
        )

    if ocr_attempted and ocr_unavailable:
        return ExtractionResult(
            text="",
            status="ocr_unavailable",
            message=(
                "PDF appears image-based and OCR runtime is unavailable. "
                "Install paddleocr/paddlepaddle and PyMuPDF, then retry."
            ),
            extractor_used="pdfplumber",
        )
    return ExtractionResult(
        text="",
        status="empty_text",
        message="No extractable text found in PDF.",
        extractor_used="pdfplumber",
    )


def _extract_pdf(path: Path) -> str:
    return _extract_pdf_with_diagnostics(path).text


def _extract_docx(path: Path) -> str:
    doc = Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def _extract_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_csv(path: Path) -> str:
    rows: list[str] = []
    content = path.read_text(encoding="utf-8", errors="replace")
    reader = csv.reader(io.StringIO(content))
    for row in reader:
        rows.append(" | ".join(row))
    return "\n".join(rows)


def _extract_media(path: Path) -> str:
    """Transcribe audio/video files using OpenAI Whisper (local)."""
    return _extract_media_with_diagnostics(path).text


def _extract_image_text(path: Path) -> str:
    return _extract_image_text_with_diagnostics(path).text


def _extract_media_with_diagnostics(path: Path) -> ExtractionResult:
    try:
        model = _get_whisper_model()
        result = model.transcribe(str(path))
        text = clean_text(result.get("text", ""))
        if text:
            return ExtractionResult(
                text=text,
                status="ok",
                extractor_used="whisper",
            )
        return ExtractionResult(
            text="",
            status="empty_text",
            message="Media transcription returned no text.",
            extractor_used="whisper",
        )
    except Exception:
        logger.exception("Media transcription failed for %s", path)
        return ExtractionResult(
            text="",
            status="media_transcription_unavailable",
            message=(
                "Media transcription failed. Ensure ffmpeg is installed and "
                "whisper dependencies are available."
            ),
            extractor_used="whisper",
        )


def _extract_image_text_with_diagnostics(path: Path) -> ExtractionResult:
    if not _enable_pdf_ocr:
        return ExtractionResult(
            text="",
            status="ocr_unavailable",
            message="OCR is disabled by EXTRACTA_ENABLE_PDF_OCR=0.",
            extractor_used="none",
        )
    try:
        ocr = _get_paddle_ocr()
        result = ocr.ocr(str(path))
        lines: list[str] = []
        for line in _collect_ocr_lines(result):
            lines.append(line)
        text = clean_text("\n".join(lines))
        if text:
            return ExtractionResult(
                text=text,
                status="ok",
                extractor_used="paddleocr",
            )
        return ExtractionResult(
            text="",
            status="empty_text",
            message="No OCR text found in image.",
            extractor_used="paddleocr",
        )
    except Exception:
        logger.exception("Image OCR failed for %s", path)
        return ExtractionResult(
            text="",
            status="ocr_unavailable",
            message="Image OCR runtime unavailable (paddleocr/paddlepaddle missing).",
            extractor_used="paddleocr",
        )


def _ocr_pdf_page(path: Path, page_index: int) -> tuple[str, bool]:
    try:
        import fitz
        import numpy as np
    except Exception:
        logger.warning(
            "PDF OCR dependencies missing (PyMuPDF/numpy). Falling back to pdfplumber only."
        )
        return "", True

    try:
        doc = fitz.open(str(path))
        if page_index < 0 or page_index >= len(doc):
            doc.close()
            return "", False
        page = doc.load_page(page_index)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n
        )
        if pix.n == 4:
            img = img[:, :, :3]
        ocr = _get_paddle_ocr()
        result = ocr.ocr(img)
        doc.close()

        lines: list[str] = []
        for line in _collect_ocr_lines(result):
            lines.append(line)
        return "\n".join(lines).strip(), False
    except Exception:
        logger.exception("PDF OCR failed for %s page %d", path, page_index)
        return "", False


def _collect_ocr_lines(result: object) -> list[str]:
    """Normalize PaddleOCR v2/v3 outputs into plain text lines."""
    lines: list[str] = []
    if result is None:
        return lines

    if isinstance(result, dict):
        rec_texts = result.get("rec_texts")
        if isinstance(rec_texts, list):
            lines.extend(str(t).strip() for t in rec_texts if str(t).strip())

    def walk(node: object) -> None:
        if isinstance(node, dict):
            rec_texts = node.get("rec_texts")
            if isinstance(rec_texts, list):
                for t in rec_texts:
                    if str(t).strip():
                        lines.append(str(t).strip())
            rec_text = node.get("rec_text")
            if isinstance(rec_text, str) and rec_text.strip():
                lines.append(rec_text.strip())
            for child in node.values():
                walk(child)
            return
        if isinstance(node, str):
            if node.strip():
                lines.append(node.strip())
            return
        if isinstance(node, tuple):
            walk(list(node))
            return
        if isinstance(node, list):
            if len(node) >= 2 and isinstance(node[1], (list, tuple)):
                maybe_text = node[1][0] if node[1] else None
                if isinstance(maybe_text, str) and maybe_text.strip():
                    lines.append(maybe_text.strip())
                    return
            for child in node:
                walk(child)

    walk(result)
    deduped: list[str] = []
    seen = set()
    for line in lines:
        if line not in seen:
            seen.add(line)
            deduped.append(line)
    return deduped


_EXTRACTORS = {
    ".pdf": _extract_pdf,
    ".docx": _extract_docx,
    ".txt": _extract_txt,
    ".csv": _extract_csv,
    ".jpg": _extract_image_text,
    ".jpeg": _extract_image_text,
    ".png": _extract_image_text,
    ".mp3": _extract_media,
    ".wav": _extract_media,
    ".m4a": _extract_media,
    ".mp4": _extract_media,
    ".webm": _extract_media,
    ".mkv": _extract_media,
}
