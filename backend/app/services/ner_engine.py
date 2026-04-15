from __future__ import annotations

import logging
from dataclasses import dataclass, field

from gliner import GLiNER

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "urchade/gliner_multi-v2.1"

DEFAULT_LABELS = [
    "person",
    "organization",
    "location",
    "date",
    "money",
    "communication platform",
    "email",
    "phone",
    "ic number",
]

MAX_CHUNK_LENGTH = 1500


@dataclass
class ExtractedEntity:
    text: str
    label: str
    score: float
    start: int
    end: int


class NEREngine:
    """Wraps GLiNER for named entity recognition with configurable labels."""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self.model: GLiNER | None = None

    def load_model(self) -> None:
        logger.info("Loading NER model: %s", self.model_name)
        self.model = GLiNER.from_pretrained(self.model_name)
        logger.info("NER model loaded successfully")

    def predict(
        self,
        text: str,
        labels: list[str] | None = None,
        threshold: float = 0.3,
    ) -> list[ExtractedEntity]:
        if self.model is None:
            raise RuntimeError("NER model not loaded. Call load_model() first.")

        labels = labels or DEFAULT_LABELS
        chunks = self._chunk_text(text)
        entities: list[ExtractedEntity] = []

        for chunk_offset, chunk in chunks:
            raw_entities = self.model.predict_entities(
                chunk, labels, threshold=threshold
            )
            for ent in raw_entities:
                entities.append(
                    ExtractedEntity(
                        text=ent["text"],
                        label=ent["label"],
                        score=round(ent["score"], 4),
                        start=ent["start"] + chunk_offset,
                        end=ent["end"] + chunk_offset,
                    )
                )

        return self._deduplicate_overlapping(entities)

    def _chunk_text(self, text: str) -> list[tuple[int, str]]:
        """Split long text into overlapping chunks for the model."""
        if len(text) <= MAX_CHUNK_LENGTH:
            return [(0, text)]

        chunks: list[tuple[int, str]] = []
        stride = MAX_CHUNK_LENGTH - 200
        for i in range(0, len(text), stride):
            chunk = text[i : i + MAX_CHUNK_LENGTH]
            chunks.append((i, chunk))
            if i + MAX_CHUNK_LENGTH >= len(text):
                break
        return chunks

    @staticmethod
    def _deduplicate_overlapping(
        entities: list[ExtractedEntity],
    ) -> list[ExtractedEntity]:
        """Remove overlapping entities, keeping higher-scored ones."""
        if not entities:
            return entities

        sorted_ents = sorted(entities, key=lambda e: (-e.score, e.start))
        kept: list[ExtractedEntity] = []
        used_spans: list[tuple[int, int]] = []

        for ent in sorted_ents:
            overlaps = any(
                not (ent.end <= s or ent.start >= e) for s, e in used_spans
            )
            if not overlaps:
                kept.append(ent)
                used_spans.append((ent.start, ent.end))

        return sorted(kept, key=lambda e: e.start)
