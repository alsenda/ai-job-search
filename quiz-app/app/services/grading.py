"""Scoring and level-progression rules.

Progression rule (the "80% gate"):

- Level 1 of every track is always unlocked.
- A level is *passed* when the player has attempted at least
  ``MIN_COVERAGE`` of its questions and the mean score of the **latest**
  answer per question is at least ``PASS_THRESHOLD``.
- Level N+1 unlocks when level N is passed.

Using the latest answer per question means you can always retake a level to
improve (or lose) your standing, like re-running a test suite.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Answer, Question, QuestionSet
from app.schemas import SELF_RATING_SCORES, QuestionType, SelfRating

PASS_THRESHOLD = 0.8
MIN_COVERAGE = 0.5


def score_answer(
    question: Question,
    chosen_index: int | None,
    self_rating: SelfRating | None,
) -> float:
    """Return the score in [0, 1] for an answer to ``question``.

    Raises:
        ValueError: if the answer kind does not match the question type.
    """
    if question.type == QuestionType.MC:
        if chosen_index is None:
            raise ValueError("multiple-choice questions require chosen_index")
        return 1.0 if chosen_index == question.correct_index else 0.0
    if self_rating is None:
        raise ValueError("flashcard questions require self_rating")
    return SELF_RATING_SCORES[self_rating]


def latest_scores_by_question(session: Session, track: str) -> dict[str, float]:
    """Map question_id -> score of the most recent answer, for one track."""
    rows = session.execute(
        select(Answer.question_id, Answer.score)
        .join(Question, Answer.question_id == Question.id)
        .join(QuestionSet, Question.set_id == QuestionSet.id)
        .where(QuestionSet.track == track)
        .order_by(Answer.answered_at, Answer.id)
    ).all()
    # Later rows overwrite earlier ones, leaving the latest answer per question.
    return {question_id: score for question_id, score in rows}


def level_question_ids(session: Session, track: str, level: int) -> list[str]:
    """All question ids belonging to a track's sets at the given level."""
    rows = session.execute(
        select(Question.id)
        .join(QuestionSet, Question.set_id == QuestionSet.id)
        .where(QuestionSet.track == track, QuestionSet.level == level)
    ).all()
    return [row[0] for row in rows]


def level_stats(
    question_ids: list[str], latest_scores: dict[str, float]
) -> tuple[int, float | None, bool]:
    """Return (attempted_count, accuracy, passed) for one level's questions."""
    attempted = [latest_scores[qid] for qid in question_ids if qid in latest_scores]
    if not attempted:
        return 0, None, False
    accuracy = sum(attempted) / len(attempted)
    coverage = len(attempted) / len(question_ids) if question_ids else 0.0
    passed = coverage >= MIN_COVERAGE and accuracy >= PASS_THRESHOLD
    return len(attempted), accuracy, passed
