"""Knowledge base loader and simple RAG interface."""
from __future__ import annotations
from typing import List, Optional
from pathlib import Path

KB_PATH = Path(__file__).parent.parent.parent / "knowledge_base"

def load_knowledge_base() -> dict[str, str]:
    kb = {}
    kb_path = KB_PATH
    if kb_path.exists():
        for md_file in kb_path.glob("*.md"):
            with open(md_file, "r", encoding="utf-8") as f:
                kb[md_file.stem] = f.read()
    return kb

def search_knowledge_base(query: str, kb: Optional[dict] = None) -> List[str]:
    if kb is None: kb = load_knowledge_base()
    results = []
    query_lower = query.lower()
    for topic, content in kb.items():
        if query_lower in content.lower(): results.append(f"## {topic}\n{content}")
    return results[:5]