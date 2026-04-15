import re


_SENTENCE_RE = re.compile(r'(?<=[.!?])\s+(?=[A-Z"])')
_PARAGRAPH_RE = re.compile(r'\n\s*\n')


def split_sentences(text: str) -> list[str]:
    """Split text into sentences using punctuation boundaries."""
    sentences = _SENTENCE_RE.split(text.strip())
    return [s.strip() for s in sentences if s.strip()]


def split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs on double newlines."""
    paragraphs = _PARAGRAPH_RE.split(text.strip())
    return [p.strip() for p in paragraphs if p.strip()]


def get_sentence_spans(text: str) -> list[tuple[int, int, str]]:
    """Return (start, end, sentence_text) for every sentence in text."""
    spans: list[tuple[int, int, str]] = []
    offset = 0
    for sentence in split_sentences(text):
        start = text.find(sentence, offset)
        if start == -1:
            start = offset
        end = start + len(sentence)
        spans.append((start, end, sentence))
        offset = end
    return spans


def clean_text(text: str) -> str:
    """Normalize whitespace while preserving paragraph breaks."""
    text = re.sub(r'[^\S\n]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
