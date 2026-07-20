"""Shared fixtures: each test gets a fresh SQLite database and API client."""

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import config, db  # noqa: E402


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """TestClient backed by a throwaway SQLite file.

    The settings/engine accessors are lru_cached, so the caches are cleared
    before and after to keep tests isolated from each other and from any
    developer database.
    """
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
    db.get_session_factory.cache_clear()

    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client

    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
    db.get_session_factory.cache_clear()


def make_question(question_id: str, *, correct_index: int = 0) -> dict:
    """A minimal valid multiple-choice question."""
    return {
        "id": question_id,
        "type": "mc",
        "topic": "Transformers",
        "prompt": "What does the attention mechanism compute over the input sequence?",
        "options": ["Pairwise token relevance", "Gradient norms", "Layer count"],
        "correct_index": correct_index,
        "answer_notes": "Attention scores weight how much each token attends to every other token.",
        "difficulty_rationale": "Definitional recall question.",
        "tags": {"difficulty": "basic", "typicality": "staple", "topics": ["attention"]},
    }


def make_flashcard(question_id: str) -> dict:
    """A minimal valid flashcard question."""
    return {
        "id": question_id,
        "type": "flashcard",
        "topic": "RAG",
        "prompt": "Walk through the failure modes of a naive RAG pipeline and how you'd fix each.",
        "answer_notes": "Retrieval misses, stale chunks, context overflow; fix with hybrid search, "
        "re-ranking, chunking strategy, and eval-driven iteration.",
        "difficulty_rationale": "Open-ended synthesis across the whole pipeline.",
        "tags": {"difficulty": "advanced", "typicality": "common", "topics": ["rag"]},
    }


def make_set(
    set_id: str,
    *,
    track: str = "ai-engineer",
    level: int = 1,
    questions: list[dict] | None = None,
) -> dict:
    """A minimal valid question set."""
    return {
        "id": set_id,
        "title": f"Test set {set_id}",
        "track": track,
        "level": level,
        "questions": questions or [make_question(f"q{i}") for i in range(1, 5)],
    }
