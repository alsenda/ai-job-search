"""Validate question-set JSON files and load them into the database.

Usage (from the quiz-app directory):

    python scripts/seed.py                      # validate + load every set in data/question_sets/
    python scripts/seed.py --validate           # validate only, touch nothing
    python scripts/seed.py --validate FILE.json # validate one file (used by the quiz-forge skill)
    python scripts/seed.py FILE.json            # validate + load a single file

Exit code is non-zero if any file fails validation, so this can gate commits/CI.
"""

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas import QuestionSetFile  # noqa: E402

DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "question_sets"


def validate_file(path: Path) -> QuestionSetFile | None:
    """Parse and validate one JSON file; print errors and return None on failure."""
    try:
        data = QuestionSetFile.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as error:
        print(f"FAIL  {path.name}: invalid JSON — {error}")
        return None
    except ValidationError as error:
        print(f"FAIL  {path.name}:\n{error}")
        return None
    print(f"ok    {path.name}: {data.track} L{data.level}, {len(data.questions)} questions")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path, help="specific files (default: all sets)")
    parser.add_argument("--validate", action="store_true", help="validate only, do not load")
    args = parser.parse_args()

    paths = args.files or sorted(DEFAULT_DATA_DIR.glob("*.json"))
    if not paths:
        print(f"No question-set files found in {DEFAULT_DATA_DIR}")
        return 1

    validated = [validate_file(path) for path in paths]
    if any(v is None for v in validated):
        return 1
    if args.validate:
        print(f"All {len(validated)} file(s) valid.")
        return 0

    # Import DB modules only when actually loading, so --validate needs no database.
    from app.db import get_session_factory, init_db
    from app.services.question_sets import upsert_question_set

    init_db()
    with get_session_factory()() as session:
        for data in validated:
            assert data is not None  # narrowed by the check above
            upsert_question_set(session, data)
    print(f"Loaded {len(validated)} set(s) into the database.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
