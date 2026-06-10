"""Knowledge base RAG engine: BM25 scoring, caching, chunk assembly.

Replaces the original token-overlap implementation with BM25 retrieval,
LRU-cached loading, metadata-enriched chunks, and proper context assembly.
"""

from __future__ import annotations

import math
import re
import time
from functools import lru_cache

from ..config import KB_PATH

MAX_CHARS_PER_CHUNK = 1200
CHUNK_OVERLAP = 200
CONTEXT_WINDOW_CHARS = 3000

_STOP_WORDS: frozenset[str] = frozenset(
    {
        "il",
        "lo",
        "la",
        "i",
        "gli",
        "le",
        "un",
        "uno",
        "una",
        "di",
        "a",
        "da",
        "in",
        "con",
        "su",
        "per",
        "tra",
        "fra",
        "che",
        "e",
        "ma",
        "o",
        "non",
        "come",
        "quando",
        "dove",
        "perche",
        "quale",
        "questo",
        "quella",
        "questi",
        "quelle",
        "mio",
        "mia",
        "miei",
        "mie",
        "tuo",
        "tua",
        "tuoi",
        "tue",
        "suo",
        "sua",
        "suoi",
        "sue",
        "nostro",
        "nostra",
        "nostri",
        "nostre",
        "vostro",
        "vostra",
        "essere",
        "avere",
        "andare",
        "fare",
        "potere",
        "dovere",
        "volere",
        "sapere",
        "vedere",
        "dare",
        "stare",
        "venire",
        "dire",
        "the",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "shall",
        "should",
        "may",
        "might",
        "must",
        "can",
        "could",
        "of",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "about",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "out",
        "off",
        "over",
        "under",
        "again",
        "further",
        "then",
        "once",
        "here",
        "there",
        "when",
        "where",
        "why",
        "how",
        "all",
        "both",
        "each",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "nor",
        "not",
        "only",
        "own",
        "same",
        "so",
        "than",
        "too",
        "very",
        "just",
        "because",
        "but",
        "and",
        "or",
        "if",
        "while",
        "that",
        "this",
        "these",
        "those",
        "it",
        "its",
    }
)


def _tokenize(text: str) -> list[str]:
    """Tokenize text: lowercase, strip non-alpha chars, remove stop-words."""
    raw = re.findall(r"[a-z0-9àèéìòù]+", text.lower())
    return [t for t in raw if t not in _STOP_WORDS and len(t) > 1]


def _split_text(text: str) -> list[str]:
    """Split markdown text into overlapping chunks respecting boundaries."""
    cleaned = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(cleaned) <= MAX_CHARS_PER_CHUNK:
        return [cleaned]
    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = start + MAX_CHARS_PER_CHUNK
        chunk = cleaned[start:end]
        if end < len(cleaned):
            best_pos = end
            for sep in ("\n\n", ". ", "! ", "? ", "\n", " "):
                pos = chunk.rfind(sep)
                if pos > MAX_CHARS_PER_CHUNK // 3:
                    best_pos = start + pos + len(sep)
                    break
            end = best_pos
            chunk = cleaned[start:end]
        chunk = chunk.strip()
        if chunk:
            chunks.append(chunk)
        start = end - CHUNK_OVERLAP
        if start < 0:
            start = 0
    return chunks


@lru_cache(maxsize=4)
def _cached_load(kb_mtime: float) -> list[dict]:
    """Cached chunk loader keyed by the directory modification time."""
    chunks: list[dict] = []
    if not KB_PATH.exists():
        return chunks
    for md_file in sorted(KB_PATH.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        topic = md_file.stem
        parts = _split_text(text)
        for idx, part in enumerate(parts):
            chunk_tokens = _tokenize(part + " " + topic)
            heading = _extract_heading(part)
            chunks.append(
                {
                    "topic": topic,
                    "chunk_id": f"{topic}::{idx}",
                    "text": part,
                    "word_count": len(part.split()),
                    "char_count": len(part),
                    "token_count": len(chunk_tokens),
                    "section": heading or topic,
                }
            )
    return chunks


def _extract_heading(text: str) -> str:
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("#"):
            return s.lstrip("#").strip()
    return ""


def load_chunks(force_reload: bool = False) -> list[dict]:
    """Load and cache all KB chunks with BM25-ready metadata.

    Cache key is the modification time of the knowledge_base directory.
    Call with force_reload=True to bypass the cache.

    Args:
        force_reload: if True, clear the LRU cache and load from disk.

    Returns:
        List of chunk dicts with keys: topic, chunk_id, text, word_count,
        char_count, token_count, section.
    """
    if force_reload:
        _cached_load.cache_clear()
    mtime = KB_PATH.stat().st_mtime if KB_PATH.exists() else 0.0
    return _cached_load(mtime)


# ---------------------------------------------------------------------------
# BM25 scoring
# ---------------------------------------------------------------------------


def _bm25_score(
    query_tokens: list[str],
    chunk: dict,
    avg_dl: float,
    idf: dict[str, float],
) -> float:
    """Compute BM25 relevance score for a single chunk."""
    k1, b = 1.5, 0.75
    text_tokens = _tokenize(chunk["text"] + " " + chunk.get("section", ""))
    tf: dict[str, int] = {}
    for t in text_tokens:
        tf[t] = tf.get(t, 0) + 1
    dl = max(1, chunk.get("token_count", len(text_tokens)))
    score = 0.0
    for tok in query_tokens:
        if tok in tf and tok in idf:
            f = tf[tok]
            score += idf[tok] * (f * (k1 + 1)) / (f + k1 * (1 - b + b * (dl / avg_dl)))
    return score


def _build_bm25_index(chunks: list[dict]) -> tuple[float, dict[str, float]]:
    """Return (avg_doc_length, idf_table) for BM25 scoring."""
    n = len(chunks)
    if n == 0:
        return 1.0, {}
    total_tokens = sum(c["token_count"] for c in chunks)
    avg_dl = max(1.0, total_tokens / n)

    doc_freq: dict[str, int] = {}
    for c in chunks:
        seen: set[str] = set()
        text = c["text"] + " " + c.get("section", "")
        for tok in _tokenize(text):
            if tok not in seen:
                doc_freq[tok] = doc_freq.get(tok, 0) + 1
                seen.add(tok)

    idf: dict[str, float] = {}
    for tok, df in doc_freq.items():
        idf[tok] = math.log((n - df + 0.5) / (df + 0.5) + 1.0)
    return avg_dl, idf


# ---------------------------------------------------------------------------
# Public search API
# ---------------------------------------------------------------------------


def search_knowledge_base(
    query: str,
    max_chunks: int = 4,
    min_score: float = 0.05,
    as_string: bool = False,
) -> list[dict] | str:
    """BM25-ranked search over the knowledge base.

    Args:
        query:      Natural-language query in Italian or English.
        max_chunks:  Cap on the number of chunks returned.
        min_score:   BM25 score cutoff (0 disables the filter).
        as_string:   If True, return a formatted string (backward-compatible output).

    Returns:
        Ordered list of chunk dicts with a ``score`` field, or a formatted
        string if ``as_string=True``.
    """
    chunks = load_chunks()
    if not chunks:
        return "" if as_string else []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return "" if as_string else []

    avg_dl, idf = _build_bm25_index(chunks)

    scored: list[tuple[float, dict]] = []
    for ch in chunks:
        s = _bm25_score(query_tokens, ch, avg_dl, idf)
        if s >= min_score:
            scored.append((s, ch))

    scored.sort(key=lambda x: x[0], reverse=True)

    results: list[dict] = []
    total_chars = 0
    for score, ch in scored[:max_chunks]:
        results.append({**ch, "score": round(score, 4)})
        total_chars += ch["char_count"]
        if total_chars >= CONTEXT_WINDOW_CHARS:
            break
    if as_string:
        return format_context_for_llm(results)
    return results


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def list_topics() -> list[str]:
    """Return sorted list of knowledge-base topic names (file stems)."""
    if not KB_PATH.exists():
        return []
    return sorted(f.stem for f in KB_PATH.glob("*.md"))


def get_kb_stats() -> dict:
    """Return metadata about the loaded knowledge base."""
    chunks = load_chunks()
    topics: dict[str, int] = {}
    total_words = 0
    total_chars = 0
    for c in chunks:
        t = c["topic"]
        topics[t] = topics.get(t, 0) + 1
        total_words += c["word_count"]
        total_chars += c["char_count"]
    return {
        "total_chunks": len(chunks),
        "total_topics": len(topics),
        "topics": sorted(topics.keys()),
        "chunks_per_topic": topics,
        "total_words": total_words,
        "total_chars": total_chars,
        "kb_path": str(KB_PATH),
        "chunk_size": MAX_CHARS_PER_CHUNK,
        "overlap": CHUNK_OVERLAP,
    }


def format_context_for_llm(results: list[dict], max_chars: int = CONTEXT_WINDOW_CHARS) -> str:
    """Format ranked chunks for inclusion in an LLM prompt.

    Respects ``max_chars`` to keep the context window in bounds.
    """
    if not results:
        return ""
    parts: list[str] = []
    total = 0
    for r in results:
        header = f"[{r.get('section', r['topic'])} - {r['topic']}]"
        entry = f"{header}\n{r['text'].strip()}"
        if total + len(entry) > max_chars:
            break
        parts.append(entry)
        total += len(entry)
    return "\n\n---\n\n".join(parts)


def reload_kb() -> dict:
    """Flush the LRU cache and reload all KB files from disk."""
    _cached_load.cache_clear()
    n = load_chunks(force_reload=True)
    return {
        "status": "reloaded",
        "chunks_loaded": len(n),
        "timestamp": time.time(),
    }
