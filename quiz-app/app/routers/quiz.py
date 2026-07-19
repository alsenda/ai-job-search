"""Quiz-session endpoints: start a session, answer cards, finish."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Answer, Question, QuizSession, utcnow
from app.schemas import AnswerRequest, AnswerResult, QuestionOut, SessionOut, SessionStartRequest
from app.services import grading, question_sets, stats

router = APIRouter(prefix="/api/quiz", tags=["quiz"])


def _question_out(question: Question) -> QuestionOut:
    return QuestionOut(
        id=question.id,
        set_id=question.set_id,
        type=question.type,  # type: ignore[arg-type]
        topic=question.topic,
        prompt=question.prompt,
        options=question.options,
        correct_index=question.correct_index,
        answer_notes=question.answer_notes,
        difficulty_rationale=question.difficulty_rationale,
        tags=question_sets.tags_of(question),
    )


@router.post("/start")
def start_session(
    request: SessionStartRequest, session: Session = Depends(get_session)
) -> SessionOut:
    """Create a session and return its cards (weakest questions first)."""
    if request.mode == "level":
        if request.level is None:
            raise HTTPException(status_code=422, detail="mode 'level' requires a level")
        progress = stats.track_progress(session, request.track)
        level_info = next(lp for lp in progress.levels if lp.level == request.level)
        if not level_info.unlocked:
            raise HTTPException(
                status_code=403,
                detail=f"Level {request.level} is locked — pass level {request.level - 1} "
                f"(≥{int(grading.PASS_THRESHOLD * 100)}% on at least "
                f"{int(grading.MIN_COVERAGE * 100)}% of its questions) first.",
            )

    latest = grading.latest_scores_by_question(session, request.track)
    questions = question_sets.select_questions(
        session=session,
        track=request.track,
        level=request.level,
        typicality=request.typicality,
        latest_scores=latest,
        limit=request.limit,
    )
    if not questions:
        raise HTTPException(status_code=404, detail="No questions match this selection.")

    quiz_session = QuizSession(
        id=str(uuid.uuid4()), track=request.track, level=request.level, mode=request.mode
    )
    session.add(quiz_session)
    session.commit()
    return SessionOut(
        id=quiz_session.id,
        track=quiz_session.track,
        level=quiz_session.level,
        mode=quiz_session.mode,
        questions=[_question_out(q) for q in questions],
    )


@router.post("/answer")
def submit_answer(request: AnswerRequest, session: Session = Depends(get_session)) -> AnswerResult:
    """Grade one answer and persist it."""
    quiz_session = session.get(QuizSession, request.session_id)
    if quiz_session is None:
        raise HTTPException(status_code=404, detail="Unknown session.")
    question = session.get(Question, request.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Unknown question.")

    try:
        score = grading.score_answer(question, request.chosen_index, request.self_rating)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    session.add(
        Answer(
            session_id=quiz_session.id,
            question_id=question.id,
            score=score,
            chosen_index=request.chosen_index,
            self_rating=request.self_rating,
        )
    )
    session.commit()
    return AnswerResult(
        question_id=question.id,
        score=score,
        correct=score >= 1.0,
        correct_index=question.correct_index,
        answer_notes=question.answer_notes,
    )


@router.post("/{session_id}/finish")
def finish_session(session_id: str, session: Session = Depends(get_session)) -> dict[str, str]:
    """Mark a session as finished (used by the UI to close a run)."""
    quiz_session = session.get(QuizSession, session_id)
    if quiz_session is None:
        raise HTTPException(status_code=404, detail="Unknown session.")
    quiz_session.finished_at = utcnow()
    session.commit()
    return {"status": "finished"}
