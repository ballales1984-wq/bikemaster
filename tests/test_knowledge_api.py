"""Test knowledge base API."""
import os

from bike_analyzer.backend.analytics.knowledge_base import load_chunks, search_knowledge_base


def test_load_chunks():
    chunks = load_chunks()
    assert isinstance(chunks, list)


def test_search_knowledge_base_empty():
    results = search_knowledge_base("")
    assert results == "" or isinstance(results, str)


def test_search_knowledge_base_training():
    results = search_knowledge_base("allenamento")
    assert isinstance(results, str)


def test_search_knowledge_base_recovery():
    results = search_knowledge_base("recupero")
    assert isinstance(results, str)