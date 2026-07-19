"""Question-set contract tests, including validation of every shipped seed file."""

import json
from pathlib import Path

import pytest
from app.schemas import QuestionSetFile
from pydantic import ValidationError
from tests.conftest import make_flashcard, make_question, make_set

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "question_sets"


def test_valid_set_parses():
    data = make_set("valid-set", questions=[make_question("q1"), make_flashcard("q2")])
    parsed = QuestionSetFile.model_validate(data)
    assert parsed.level == 1
    assert len(parsed.questions) == 2


def test_mc_requires_correct_index():
    question = make_question("q1")
    del question["correct_index"]
    with pytest.raises(ValidationError, match="requires options and correct_index"):
        QuestionSetFile.model_validate(make_set("bad-set", questions=[question]))


def test_mc_correct_index_must_be_in_range():
    question = make_question("q1", correct_index=7)
    with pytest.raises(ValidationError, match="out of range"):
        QuestionSetFile.model_validate(make_set("bad-set", questions=[question]))


def test_flashcard_must_not_have_options():
    question = make_flashcard("q1")
    question["options"] = ["a", "b"]
    with pytest.raises(ValidationError, match="must not have options"):
        QuestionSetFile.model_validate(make_set("bad-set", questions=[question]))


def test_duplicate_question_ids_rejected():
    with pytest.raises(ValidationError, match="duplicate question id"):
        QuestionSetFile.model_validate(
            make_set("bad-set", questions=[make_question("q1"), make_question("q1")])
        )


def test_level_bounds():
    with pytest.raises(ValidationError):
        QuestionSetFile.model_validate(make_set("bad-set", level=6))


@pytest.mark.parametrize("path", sorted(SEED_DIR.glob("*.json")), ids=lambda p: p.name)
def test_seed_file_is_valid(path: Path):
    """Every question set shipped in data/question_sets/ must satisfy the contract."""
    parsed = QuestionSetFile.model_validate(json.loads(path.read_text(encoding="utf-8")))
    assert len(parsed.questions) >= 8, f"{path.name} should have at least 8 questions"


def test_seed_library_is_complete():
    """3 tracks x 5 levels of seed content must exist."""
    sets = [
        QuestionSetFile.model_validate(json.loads(p.read_text(encoding="utf-8")))
        for p in SEED_DIR.glob("*.json")
    ]
    coverage = {(s.track, s.level) for s in sets}
    for track in ("ai-engineer", "tech-lead", "developer"):
        for level in range(1, 6):
            assert (track, level) in coverage, f"missing seed set for {track} level {level}"
