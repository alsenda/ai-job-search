"""Progress and export endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import ExportSummary, TrackProgress
from app.services import stats

router = APIRouter(prefix="/api/results", tags=["results"])


@router.get("/tracks")
def list_tracks(session: Session = Depends(get_session)) -> list[str]:
    """Distinct tracks available in the loaded question sets."""
    return stats.all_tracks(session)


@router.get("/progress")
def progress(track: str, session: Session = Depends(get_session)) -> TrackProgress:
    """Per-level progress (locks, accuracy, pass state) for one track."""
    return stats.track_progress(session, track)


@router.get("/export")
def export(session: Session = Depends(get_session)) -> ExportSummary:
    """Full performance summary.

    This is the machine-readable feed for the quiz-forge skill: it reads the
    weak topics and per-track levels here to generate harder question sets.
    """
    return stats.export_summary(session)
