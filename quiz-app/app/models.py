"""SQLAlchemy ORM models.

Four tables:

- ``question_sets``: a versioned bundle of questions (one track, one level)
- ``questions``: individual cards belonging to a set
- ``quiz_sessions``: one run through a selection of cards
- ``answers``: every answer ever given, the raw material for all statistics

Questions keep their authored string IDs (``<set_id>::<question_id>``) so a
re-seed after editing a JSON file updates in place instead of duplicating.
"""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    """Timezone-aware UTC timestamp (SQLite stores it naive, Postgres aware)."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Declarative base for all models."""


class QuestionSet(Base):
    __tablename__ = "question_sets"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    track: Mapped[str] = mapped_column(String(60), index=True)
    level: Mapped[int] = mapped_column(Integer, index=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    questions: Mapped[list["Question"]] = relationship(
        back_populates="question_set", cascade="all, delete-orphan"
    )


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(200), primary_key=True)
    set_id: Mapped[str] = mapped_column(ForeignKey("question_sets.id"), index=True)
    type: Mapped[str] = mapped_column(String(20))  # "mc" | "flashcard"
    topic: Mapped[str] = mapped_column(String(120), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    options: Mapped[list[str] | None] = mapped_column(JSON, default=None)
    correct_index: Mapped[int | None] = mapped_column(Integer, default=None)
    answer_notes: Mapped[str] = mapped_column(Text)
    difficulty_rationale: Mapped[str] = mapped_column(Text)
    difficulty_tag: Mapped[str] = mapped_column(String(20), index=True)
    typicality_tag: Mapped[str] = mapped_column(String(20), index=True)
    topic_tags: Mapped[list[str]] = mapped_column(JSON, default=list)

    question_set: Mapped[QuestionSet] = relationship(back_populates="questions")


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # uuid4
    track: Mapped[str] = mapped_column(String(60), index=True)
    level: Mapped[int | None] = mapped_column(Integer, default=None)
    mode: Mapped[str] = mapped_column(String(30))  # "level" | "typical-drill" | "custom"
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    answers: Mapped[list["Answer"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("quiz_sessions.id"), index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"), index=True)
    # Score in [0, 1]: MC answers are 0 or 1; flashcard self-ratings map to
    # missed=0.0, partial=0.5, nailed=1.0. One column keeps stats queries simple.
    score: Mapped[float] = mapped_column(Float)
    chosen_index: Mapped[int | None] = mapped_column(Integer, default=None)
    self_rating: Mapped[str | None] = mapped_column(String(10), default=None)
    answered_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    session: Mapped[QuizSession] = relationship(back_populates="answers")
