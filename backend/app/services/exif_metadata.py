"""Extract embedded metadata: EXIF from images, PDF document info (+ embedded images), DOCX core props, audio/video tags."""

from __future__ import annotations

import io
import json
import logging
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}
_PDF_SUFFIX = ".pdf"
_DOCX_SUFFIX = ".docx"
_AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}
_VIDEO_SUFFIXES = {".mp4", ".webm", ".mkv"}
_TEXT_NO_META = {".txt", ".csv"}


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, bytes):
        if len(value) > 200:
            return f"<{len(value)} bytes binary>"
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    t = type(value).__name__
    if t in ("IFDRational", "Fraction"):
        try:
            return float(value)
        except (TypeError, ValueError, ZeroDivisionError):
            return str(value)
    # datetime etc.
    try:
        return str(value)
    except Exception:
        return "<unserializable>"


def _pil_exif_dict(img) -> dict[str, Any]:
    """Build EXIF map from an open PIL Image."""
    try:
        from PIL.ExifTags import TAGS
    except ImportError:
        return {}
    out: dict[str, Any] = {}
    exif = img.getexif()
    if exif is None or len(exif) == 0:
        return {}
    for key, value in exif.items():
        name = TAGS.get(key, f"Tag_{key}")
        out[str(name)] = _json_safe(value)
    return out


def _extract_image_raster(path: Path) -> dict[str, Any]:
    try:
        from PIL import Image
    except ImportError:
        return {}

    try:
        with Image.open(path) as img:
            return _pil_exif_dict(img)
    except OSError:
        return {}
    except Exception:
        return {}


def _extract_exif_from_image_bytes(data: bytes) -> dict[str, Any]:
    try:
        from PIL import Image
    except ImportError:
        return {}
    try:
        with Image.open(io.BytesIO(data)) as img:
            return _pil_exif_dict(img)
    except Exception:
        return {}


def _extract_pdf(path: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return out

    try:
        doc = fitz.open(path)
    except Exception as e:
        logger.debug("PDF open failed for metadata: %s", e)
        return out

    try:
        meta = doc.metadata or {}
        clean: dict[str, Any] = {}
        for k, v in meta.items():
            if v is None or v == "":
                continue
            clean[str(k)] = _json_safe(v)
        if clean:
            out["PDF document"] = clean

        # First embedded raster with EXIF (often screenshots or photos pasted into PDFs)
        for page_idx in range(doc.page_count):
            for img_info in doc.get_page_images(page_idx):
                xref = img_info[0]
                try:
                    base = doc.extract_image(xref)
                except Exception:
                    continue
                raw = base.get("image")
                if not raw:
                    continue
                exif_part = _extract_exif_from_image_bytes(raw)
                if exif_part:
                    out["Embedded image EXIF"] = exif_part
                    break
            if "Embedded image EXIF" in out:
                break
    finally:
        doc.close()

    return out


def _extract_docx(path: Path) -> dict[str, Any]:
    try:
        from docx import Document
    except ImportError:
        return {}

    try:
        d = Document(path)
        cp = d.core_properties
        fields = {
            "title": cp.title,
            "subject": cp.subject,
            "creator": cp.author,
            "keywords": cp.keywords,
            "description": cp.comments,
            "last_modified_by": cp.last_modified_by,
            "revision": cp.revision,
            "created": str(cp.created) if cp.created else None,
            "modified": str(cp.modified) if cp.modified else None,
            "category": cp.category,
            "language": cp.language,
        }
        clean = {k: _json_safe(v) for k, v in fields.items() if v not in (None, "")}
        return {"Word document": clean} if clean else {}
    except Exception as e:
        logger.debug("DOCX metadata failed: %s", e)
        return {}


def _extract_mutagen(path: Path) -> dict[str, Any]:
    try:
        from mutagen import File as MutagenFile
    except ImportError:
        return {}

    try:
        audio = MutagenFile(path)
        if audio is None:
            return {}
        flat: dict[str, Any] = {}
        if hasattr(audio, "tags") and audio.tags:
            for k, v in audio.tags.items():
                key = str(k)
                if hasattr(v, "text"):
                    flat[key] = _json_safe(v.text[0] if v.text else "")
                else:
                    flat[key] = _json_safe(v)
        # EasyMP4 / stream info
        if hasattr(audio, "info") and audio.info:
            info = audio.info
            if hasattr(info, "length"):
                flat["duration_seconds"] = round(float(info.length), 3)
            if hasattr(info, "bitrate"):
                flat["bitrate"] = info.bitrate
        label = "Audio / container"
        if path.suffix.lower() in _VIDEO_SUFFIXES:
            label = "Media (tags)"
        return {label: flat} if flat else {}
    except Exception as e:
        logger.debug("Mutagen failed: %s", e)
        return {}


def _extract_ffprobe(path: Path) -> dict[str, Any]:
    """Best-effort stream/format metadata for video containers."""
    try:
        r = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return {}
        data = json.loads(r.stdout)
        fmt = data.get("format") or {}
        summary: dict[str, Any] = {}
        if fmt.get("duration"):
            summary["duration_seconds"] = round(float(fmt["duration"]), 3)
        br = fmt.get("bit_rate")
        if br is not None:
            try:
                summary["bitrate_kbps"] = int(str(br)) // 1000
            except (TypeError, ValueError):
                summary["bitrate"] = br
        if fmt.get("format_long_name"):
            summary["format"] = fmt["format_long_name"]
        if fmt.get("tags"):
            summary["container_tags"] = {str(k): _json_safe(v) for k, v in fmt["tags"].items()}
        streams = data.get("streams") or []
        for i, st in enumerate(streams[:4]):
            entry: dict[str, Any] = {}
            for key in ("codec_type", "codec_name", "width", "height", "sample_rate", "channels"):
                if st.get(key) is not None:
                    entry[key] = st[key]
            if st.get("tags"):
                entry["tags"] = {str(k): _json_safe(v) for k, v in st["tags"].items()}
            if entry:
                summary[f"stream_{i}"] = entry
        return {"Video / audio (ffprobe)": summary} if summary else {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        logger.debug("ffprobe failed: %s", e)
        return {}


def extract_exif_metadata(file_path: str) -> dict[str, Any] | None:
    """
    Return JSON-serializable metadata for supported uploads.

    - None: unsupported extension (should not happen for uploads).
    - {}: supported but nothing extracted.
    - dict: grouped sections (EXIF tags, PDF document, Word props, mutagen, ffprobe).
    """
    path = Path(file_path)
    suf = path.suffix.lower()

    if suf in _TEXT_NO_META:
        return {}

    if suf in _IMAGE_SUFFIXES:
        part = _extract_image_raster(path)
        return part if part else {}

    if suf == _PDF_SUFFIX:
        return _extract_pdf(path)

    if suf == _DOCX_SUFFIX:
        return _extract_docx(path)

    if suf in _AUDIO_SUFFIXES:
        m = _extract_mutagen(path)
        return m if m else {}

    if suf in _VIDEO_SUFFIXES:
        m = _extract_mutagen(path)
        if m:
            return m
        fp = _extract_ffprobe(path)
        return fp if fp else {}

    return None
