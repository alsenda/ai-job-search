"""Tests for the deterministic parts of scripts/generate_questions.py.

The live Claude API call is not exercised here; these cover the prompt
construction, slugging, and the duplicate/metadata guards around it.
"""

import pytest
from app.schemas import QuestionSetFile
from scripts import generate_questions as gen
from tests.conftest import make_question, make_set


def test_slugify():
    assert gen.slugify("Kubernetes") == "kubernetes"
    assert gen.slugify("GraphQL API design!") == "graphql-api-design"
    assert gen.slugify("  ") == "topic"


def test_build_prompt_mentions_parameters_and_existing_prompts(monkeypatch):
    monkeypatch.setattr(gen, "existing_prompt_list", lambda: ["What is attention?"])
    prompt = gen.build_prompt("Kubernetes", "ai-engineer", 4, 10, "kubernetes-l4")
    assert "Kubernetes" in prompt
    assert '"expert"' in prompt  # level 4 -> expert difficulty tag
    assert "What is attention?" in prompt


def test_check_constraints_rejects_metadata_mismatch(monkeypatch):
    monkeypatch.setattr(gen, "existing_prompt_list", lambda: [])
    data = QuestionSetFile.model_validate(make_set("wrong-id", level=2))
    with pytest.raises(ValueError, match="metadata mismatch"):
        gen.check_constraints(data, track="ai-engineer", level=2, set_id="expected-id")


def test_check_constraints_rejects_duplicate_prompts(monkeypatch):
    data = QuestionSetFile.model_validate(
        make_set("new-set", questions=[make_question("q1")])
    )
    duplicate = data.questions[0].prompt
    monkeypatch.setattr(gen, "existing_prompt_list", lambda: [duplicate])
    with pytest.raises(ValueError, match="duplicate prompts"):
        gen.check_constraints(data, track="ai-engineer", level=1, set_id="new-set")


def test_check_constraints_passes_clean_set(monkeypatch):
    monkeypatch.setattr(gen, "existing_prompt_list", lambda: ["unrelated prompt"])
    data = QuestionSetFile.model_validate(make_set("clean-set"))
    gen.check_constraints(data, track="ai-engineer", level=1, set_id="clean-set")
