"""Progress and performance aggregation.

Everything here is derived from the ``answers`` table; nothing is cached or
denormalized, so the numbers are always consistent with history.
"""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Answer, Question, QuestionSet
from app.schemas import (
    DIFFICULTY_FOR_LEVEL,
    ExportSummary,
    LevelProgress,
    TopicStat,
    TrackProgress,
)
from app.services import grading

MIN_TOPIC_ATTEMPTS = 2  # a topic needs this many answers before it counts as weak/strong
TOPIC_LIST_SIZE = 8


def track_progress(session: Session, track: str) -> TrackProgress:
    """Per-level progress for one track, applying the unlock chain."""
    latest = grading.latest_scores_by_question(session, track)
    levels: list[LevelProgress] = []
    highest_unlocked = 1
    previous_passed = True  # makes level 1 unconditionally unlocked
    for level in sorted(DIFFICULTY_FOR_LEVEL):
        question_ids = grading.level_question_ids(session, track, level)
        attempted, accuracy, passed = grading.level_stats(question_ids, latest)
        unlocked = previous_passed
        if unlocked:
            highest_unlocked = level
        levels.append(
            LevelProgress(
                level=level,
                difficulty=DIFFICULTY_FOR_LEVEL[level],
                total_questions=len(question_ids),
                attempted_questions=attempted,
                accuracy=accuracy,
                unlocked=unlocked,
                passed=passed,
            )
        )
        previous_passed = passed
    return TrackProgress(track=track, levels=levels, highest_unlocked=highest_unlocked)


def all_tracks(session: Session) -> list[str]:
    """Distinct tracks that have at least one question set, alphabetical."""
    rows = session.execute(select(QuestionSet.track).distinct().order_by(QuestionSet.track)).all()
    return [row[0] for row in rows]


def topic_stats(session: Session) -> list[TopicStat]:
    """Mean score per topic across all answers, most-attempted topics included only."""
    rows = session.execute(
        select(Question.topic, func.count(Answer.id), func.avg(Answer.score))
        .join(Answer, Answer.question_id == Question.id)
        .group_by(Question.topic)
    ).all()
    return [
        TopicStat(topic=topic, attempts=attempts, accuracy=round(float(accuracy), 3))
        for topic, attempts, accuracy in rows
        if attempts >= MIN_TOPIC_ATTEMPTS
    ]


def export_summary(session: Session) -> ExportSummary:
    """The full performance export consumed by the quiz-forge skill."""
    topics = topic_stats(session)
    total_answers = session.execute(select(func.count(Answer.id))).scalar_one()
    return ExportSummary(
        generated_at=datetime.now(UTC),
        total_answers=total_answers,
        tracks=[track_progress(session, track) for track in all_tracks(session)],
        weak_topics=sorted(topics, key=lambda t: t.accuracy)[:TOPIC_LIST_SIZE],
        strong_topics=sorted(topics, key=lambda t: -t.accuracy)[:TOPIC_LIST_SIZE],
    )
