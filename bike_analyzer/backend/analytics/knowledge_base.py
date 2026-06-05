"""Knowledge base RAG engine: chunking, retrieval, context assembly."""
from __future__ import annotations
import re
from typing import List, Optional
from pathlib import Path

KB_PATH = Path(__file__).parent.parent.parent / "knowledge_base"
MAX_CHARS_PER_CHUNK = 1200
CHUNK_OVERLAP = 200

def load_chunks() -> List[dict]:
    chunks: List[dict] = []
    if not KB_PATH.exists():
        return chunks
    for md_file in sorted(KB_PATH.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        topic = md_file.stem
        parts = _split_text(text)
        for idx, part in enumerate(parts):
            chunks.append({
                "topic": topic,
                "chunk_id": f"{topic}::{idx}",
                "text": part,
            })
    return chunks


def _split_text(text: str) -> List[str]:
    cleaned = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(cleaned) <= MAX_CHARS_PER_CHUNK:
        return [cleaned]
    chunks: List[str] = []
    start = 0
    while start < len(cleaned):
        end = start + MAX_CHARS_PER_CHUNK
        chunk = cleaned[start:end]
        if end < len(cleaned):
            for sep in ["\n\n", ". ", "! ", "? ", "\n", " "]:
                pos = chunk.rfind(sep)
                if pos > MAX_CHARS_PER_CHUNK // 3:
                    chunk = chunk[: pos + len(sep)]
                    end = start + len(chunk)
                    break
        chunks.append(chunk.strip())
        start = end - CHUNK_OVERLAP
        if start < 0:
            start = 0
    return [c for c in chunks if c]


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zàèéìòù0-9]+", text.lower()))


def search_knowledge_base(query: str, max_chunks: int = 4) -> str:
    chunks = load_chunks()
    if not chunks:
        return ""
    q_tokens = _tokenize(query)
    scored: List[tuple[float, dict]] = []
    for ch in chunks:
        c_tokens = _tokenize(ch["text"])
        overlap = len(q_tokens & c_tokens)
        if overlap:
            scored.append((overlap / (len(q_tokens) + 1e-6), ch))
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [ch for _, ch in scored[:max_chunks]]
    if not selected:
        return ""
    parts: List[str] = []
    for ch in selected:
        parts.append(f"[{ch['topic']}] {ch['text'].strip()}")
    return "\n\n".join(parts)
