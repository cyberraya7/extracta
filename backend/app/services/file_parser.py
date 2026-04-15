import csv
import io
import logging
from pathlib import Path

import pdfplumber
from docx import Document

from app.utils.text_utils import clean_text

logger = logging.getLogger(__name__)

TEXT_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv"}
MEDIA_EXTENSIONS = {".mp3", ".wav", ".m4a", ".mp4", ".webm", ".mkv"}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | MEDIA_EXTENSIONS

_whisper_model = None


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        logger.info("Loading Whisper model (base)...")
        _whisper_model = whisper.load_model("base")
        logger.info("Whisper model loaded")
    return _whisper_model


def parse_file(file_path: str | Path) -> str:
    """Extract raw text from a file based on its extension."""
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")

    extractor = _EXTRACTORS[ext]
    raw = extractor(path)
    return clean_text(raw)


def _extract_pdf(path: Path) -> str:
    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    return "\n\n".join(pages)


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
    model = _get_whisper_model()
    result = model.transcribe(str(path))
    return result.get("text", "")


_EXTRACTORS = {
    ".pdf": _extract_pdf,
    ".docx": _extract_docx,
    ".txt": _extract_txt,
    ".csv": _extract_csv,
    ".mp3": _extract_media,
    ".wav": _extract_media,
    ".m4a": _extract_media,
    ".mp4": _extract_media,
    ".webm": _extract_media,
    ".mkv": _extract_media,
}
