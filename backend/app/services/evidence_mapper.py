from __future__ import annotations

from app.utils.text_utils import get_sentence_spans

CONTEXT_CHARS = 80


def build_evidence(
    text: str,
    entities: list[dict],
    document_id: str,
    document_name: str,
) -> dict:
    """Build evidence maps for individual entities and entity-pair edges.

    Returns:
        {
            "entity_evidence": {entity_id: [snippets...]},
            "edge_evidence": {"src|tgt": [snippets...]}
        }
    """
    sentence_spans = get_sentence_spans(text)
    entity_evidence: dict[str, list[dict]] = {}
    edge_evidence: dict[str, list[dict]] = {}

    for ent in entities:
        ent_snippets = _snippets_for_entity(
            text, ent, sentence_spans, document_id, document_name
        )
        entity_evidence[ent["id"]] = ent_snippets

    _build_edge_evidence(
        text, entities, sentence_spans, document_id, document_name, edge_evidence
    )

    return {
        "entity_evidence": entity_evidence,
        "edge_evidence": edge_evidence,
    }


def _snippets_for_entity(
    text: str,
    entity: dict,
    sentence_spans: list[tuple[int, int, str]],
    doc_id: str,
    doc_name: str,
) -> list[dict]:
    """Extract text snippets where an entity appears."""
    snippets: list[dict] = []
    seen_sentences: set[str] = set()

    for pos in entity["positions"]:
        sentence = _find_containing_sentence(
            pos["start"], pos["end"], sentence_spans
        )
        if sentence and sentence not in seen_sentences:
            seen_sentences.add(sentence)
            snippets.append(
                {
                    "text": sentence,
                    "entity_text": entity["text"],
                    "start": pos["start"],
                    "end": pos["end"],
                    "document_id": doc_id,
                    "document_name": doc_name,
                }
            )

    if not snippets:
        for pos in entity["positions"]:
            ctx_start = max(0, pos["start"] - CONTEXT_CHARS)
            ctx_end = min(len(text), pos["end"] + CONTEXT_CHARS)
            snippet = text[ctx_start:ctx_end].strip()
            snippets.append(
                {
                    "text": f"...{snippet}...",
                    "entity_text": entity["text"],
                    "start": pos["start"],
                    "end": pos["end"],
                    "document_id": doc_id,
                    "document_name": doc_name,
                }
            )

    return snippets


def _build_edge_evidence(
    text: str,
    entities: list[dict],
    sentence_spans: list[tuple[int, int, str]],
    doc_id: str,
    doc_name: str,
    edge_evidence: dict[str, list[dict]],
) -> None:
    """Find sentences where two entities co-occur."""
    ent_by_id = {e["id"]: e for e in entities}

    for s_start, s_end, sentence in sentence_spans:
        ents_in_sentence: list[dict] = []
        for ent in entities:
            for pos in ent["positions"]:
                if pos["start"] >= s_start and pos["end"] <= s_end:
                    ents_in_sentence.append(ent)
                    break

        if len(ents_in_sentence) < 2:
            continue

        for i, a in enumerate(ents_in_sentence):
            for b in ents_in_sentence[i + 1 :]:
                edge_key = _edge_key(a["id"], b["id"])
                if edge_key not in edge_evidence:
                    edge_evidence[edge_key] = []
                edge_evidence[edge_key].append(
                    {
                        "text": sentence,
                        "entities": [a["text"], b["text"]],
                        "document_id": doc_id,
                        "document_name": doc_name,
                    }
                )


def _find_containing_sentence(
    start: int, end: int, sentence_spans: list[tuple[int, int, str]]
) -> str | None:
    for s_start, s_end, sentence in sentence_spans:
        if start >= s_start and end <= s_end:
            return sentence
    return None


def _edge_key(a: str, b: str) -> str:
    return "|".join(sorted([a, b]))
