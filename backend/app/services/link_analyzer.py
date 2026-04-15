from __future__ import annotations

from itertools import combinations

import networkx as nx

from app.utils.text_utils import get_sentence_spans, split_paragraphs

PARAGRAPH_WEIGHT_FACTOR = 0.3


def build_graph(
    text: str,
    entities: list[dict],
) -> dict:
    """Build a co-occurrence graph from entities found in text.

    Returns {nodes: [...], edges: [...]} suitable for the frontend.
    """
    G = nx.Graph()

    _add_nodes(G, entities)
    _add_sentence_edges(G, text, entities)
    _add_paragraph_edges(G, text, entities)

    return _serialize_graph(G, entities)


def _add_nodes(G: nx.Graph, entities: list[dict]) -> None:
    for ent in entities:
        G.add_node(
            ent["id"],
            label=ent["text"],
            type=ent["label"],
            score=ent["score"],
            occurrences=ent["occurrences"],
        )


def _entities_in_span(
    entities: list[dict], start: int, end: int
) -> list[dict]:
    """Find entities that have at least one position overlapping a text span."""
    found: list[dict] = []
    for ent in entities:
        for pos in ent["positions"]:
            if pos["start"] >= start and pos["end"] <= end:
                found.append(ent)
                break
    return found


def _add_sentence_edges(
    G: nx.Graph, text: str, entities: list[dict]
) -> None:
    """Create edges for entities that co-occur in the same sentence."""
    sentence_spans = get_sentence_spans(text)

    for start, end, _ in sentence_spans:
        ents_in_sentence = _entities_in_span(entities, start, end)
        for a, b in combinations(ents_in_sentence, 2):
            _increment_edge(G, a, b, weight=1.0)


def _add_paragraph_edges(
    G: nx.Graph, text: str, entities: list[dict]
) -> None:
    """Create weaker edges for entities within the same paragraph."""
    offset = 0
    for para in split_paragraphs(text):
        p_start = text.find(para, offset)
        if p_start == -1:
            p_start = offset
        p_end = p_start + len(para)
        offset = p_end

        ents_in_para = _entities_in_span(entities, p_start, p_end)
        for a, b in combinations(ents_in_para, 2):
            if not G.has_edge(a["id"], b["id"]):
                _increment_edge(G, a, b, weight=PARAGRAPH_WEIGHT_FACTOR)


def _increment_edge(
    G: nx.Graph, a: dict, b: dict, weight: float
) -> None:
    rel_type = f"{a['label']}-{b['label']}"
    if G.has_edge(a["id"], b["id"]):
        G[a["id"]][b["id"]]["weight"] += weight
    else:
        G.add_edge(
            a["id"],
            b["id"],
            weight=weight,
            relationship=rel_type,
            source_label=a["text"],
            target_label=b["text"],
        )


def _serialize_graph(G: nx.Graph, entities: list[dict]) -> dict:
    nodes = []
    for node_id, data in G.nodes(data=True):
        nodes.append(
            {
                "id": node_id,
                "label": data.get("label", ""),
                "type": data.get("type", ""),
                "score": data.get("score", 0),
                "occurrences": data.get("occurrences", 1),
                "connections": G.degree(node_id),
            }
        )

    edges = []
    for source, target, data in G.edges(data=True):
        edges.append(
            {
                "source": source,
                "target": target,
                "weight": round(data.get("weight", 1), 2),
                "relationship": data.get("relationship", ""),
                "source_label": data.get("source_label", ""),
                "target_label": data.get("target_label", ""),
            }
        )

    return {"nodes": nodes, "edges": edges}
