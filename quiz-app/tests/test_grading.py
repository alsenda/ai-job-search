"""Unit tests for scoring and the level-progression rule."""

import pytest
from app.models import Question
from app.schemas import SelfRating
from app.services import grading


def _mc_question() -> Question:
    return Question(
        id="s::q1", set_id="s", type="mc", topic="t", prompt="p",
        options=["a", "b", "c"], correct_index=1, answer_notes="n",
        difficulty_rationale="r", difficulty_tag="basic", typicality_tag="staple",
        topic_tags=[],
    )


def _flashcard() -> Question:
    return Question(
        id="s::q2", set_id="s", type="flashcard", topic="t", prompt="p",
        options=None, correct_index=None, answer_notes="n",
        difficulty_rationale="r", difficulty_tag="basic", typicality_tag="staple",
        topic_tags=[],
    )


def test_mc_scoring():
    assert grading.score_answer(_mc_question(), 1, None) == 1.0
    assert grading.score_answer(_mc_question(), 0, None) == 0.0


def test_mc_requires_choice():
    with pytest.raises(ValueError, match="chosen_index"):
        grading.score_answer(_mc_question(), None, SelfRating.NAILED)


def test_flashcard_scoring():
    assert grading.score_answer(_flashcard(), None, SelfRating.NAILED) == 1.0
    assert grading.score_answer(_flashcard(), None, SelfRating.PARTIAL) == 0.5
    assert grading.score_answer(_flashcard(), None, SelfRating.MISSED) == 0.0


def test_flashcard_requires_rating():
    with pytest.raises(ValueError, match="self_rating"):
        grading.score_answer(_flashcard(), 0, None)


def test_level_stats_unattempted():
    attempted, accuracy, passed = grading.level_stats(["a", "b"], {})
    assert (attempted, accuracy, passed) == (0, None, False)


def test_level_stats_passes_at_threshold_with_coverage():
    ids = ["a", "b", "c", "d"]
    # 2 of 4 attempted = exactly 50% coverage; mean score 0.8 = exactly the threshold.
    attempted, accuracy, passed = grading.level_stats(ids, {"a": 1.0, "b": 0.6})
    assert attempted == 2
    assert accuracy == pytest.approx(0.8)
    assert passed


def test_level_stats_fails_below_coverage():
    ids = ["a", "b", "c", "d", "e"]
    # 2 of 5 attempted = 40% coverage: perfect accuracy still doesn't pass.
    _, accuracy, passed = grading.level_stats(ids, {"a": 1.0, "b": 1.0})
    assert accuracy == 1.0
    assert not passed


def test_level_stats_fails_below_threshold():
    ids = ["a", "b"]
    _, accuracy, passed = grading.level_stats(ids, {"a": 1.0, "b": 0.5})
    assert accuracy == pytest.approx(0.75)
    assert not passed
