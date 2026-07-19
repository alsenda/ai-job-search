"""Generate a new question set for any topic using the Claude API.

Admin usage (from the quiz-app directory, with ANTHROPIC_API_KEY set):

    python scripts/generate_questions.py --topic "Kubernetes" --track ai-engineer --level 4
    python scripts/generate_questions.py --topic "GraphQL API design" --track developer \\
        --level 3 --count 8 --seed

The response is validated against the shared ``QuestionSetFile`` schema
(app/schemas.py) — the same contract used by scripts/seed.py, the import API
endpoint, and the quiz-forge skill — so a generated set is immediately loadable
everywhere. On a validation failure the error is fed back to the model for one
retry. Existing prompts are collected first so the model avoids duplicates,
and any exact duplicate is rejected after generation as a hard check.
"""

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas import DIFFICULTY_FOR_LEVEL, QuestionSetFile  # noqa: E402

DATA_DIR = PROJECT_ROOT / "data" / "question_sets"
MODEL = "claude-opus-4-8"

PROMPT_TEMPLATE = """\
You are an expert technical interviewer creating a card-quiz question set used
for interview training (senior AI engineer / tech lead / developer roles).

Create a question set with these exact parameters:
- topic: {topic}
- track: {track}
- level: {level} (difficulty tag must be "{difficulty}")
- number of questions: {count}
- set id: {set_id}

Requirements:
1. Every question must be a REALISTIC interview question for this topic at this
   difficulty — phrased the way interviewers actually ask it.
2. Mix question types: multiple-choice ("mc", 3-5 plausible options, exactly one
   correct, distractors reflecting real misconceptions) and open "flashcard"
   questions (deep answers a candidate should be able to give verbally).
   Higher levels should lean toward flashcards.
3. answer_notes must teach: the correct answer, why, and what a strong candidate
   mentions for bonus credit. 60-150 words.
4. difficulty_rationale: one sentence on why this question sits at this level.
5. tags.typicality must honestly rate how often interviewers ask it:
   "staple" (almost always), "common", "occasional", or "curveball".
   tags.difficulty must be "{difficulty}". tags.topics: 1-4 lowercase slugs.
6. Question ids: short lowercase-hyphen slugs, unique within the set.
7. Do NOT duplicate or trivially rephrase any of these existing prompts:
{existing_prompts}
"""


def existing_prompt_list() -> list[str]:
    """All question prompts already present in the data directory."""
    prompts: list[str] = []
    for path in DATA_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        prompts.extend(q["prompt"] for q in data.get("questions", []))
    return prompts


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "topic"


def build_prompt(topic: str, track: str, level: int, count: int, set_id: str) -> str:
    existing = existing_prompt_list()
    listing = "\n".join(f'   - "{p[:120]}"' for p in existing) or "   (none yet)"
    return PROMPT_TEMPLATE.format(
        topic=topic,
        track=track,
        level=level,
        difficulty=DIFFICULTY_FOR_LEVEL[level].value,
        count=count,
        set_id=set_id,
        existing_prompts=listing,
    )


def generate(topic: str, track: str, level: int, count: int, set_id: str) -> QuestionSetFile:
    """Call Claude and return a schema-valid question set (one retry on failure)."""
    import anthropic

    client = anthropic.Anthropic()
    messages: list[dict] = [
        {"role": "user", "content": build_prompt(topic, track, level, count, set_id)}
    ]

    last_error: Exception | None = None
    for attempt in range(2):
        response = client.messages.parse(
            model=MODEL,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            messages=messages,
            output_format=QuestionSetFile,
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("The model declined this topic; try rephrasing it.")
        try:
            data = response.parsed_output
            if data is None:
                raise ValueError("model returned no parseable output")
            check_constraints(data, track=track, level=level, set_id=set_id)
            return data
        except Exception as error:  # noqa: BLE001 - feed any failure back for one retry
            last_error = error
            if attempt == 0:
                raw = next((b.text for b in response.content if b.type == "text"), "")
                messages.append({"role": "assistant", "content": raw})
                messages.append(
                    {
                        "role": "user",
                        "content": f"That output failed validation: {error}\n"
                        "Return a corrected question set that fixes this.",
                    }
                )
    raise RuntimeError(f"Generation failed after retry: {last_error}")


def check_constraints(data: QuestionSetFile, *, track: str, level: int, set_id: str) -> None:
    """Enforce parameters and the no-duplicates rule beyond schema validation."""
    if data.id != set_id or data.track != track or data.level != level:
        raise ValueError(
            f"set metadata mismatch: expected id={set_id} track={track} level={level}, "
            f"got id={data.id} track={data.track} level={data.level}"
        )
    existing = {p.strip().lower() for p in existing_prompt_list()}
    duplicates = [q.id for q in data.questions if q.prompt.strip().lower() in existing]
    if duplicates:
        raise ValueError(f"duplicate prompts (already exist in another set): {duplicates}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", required=True, help='e.g. "Kubernetes", "System design"')
    parser.add_argument("--track", default="ai-engineer", help="track slug (any, e.g. developer)")
    parser.add_argument("--level", type=int, choices=range(1, 6), required=True)
    parser.add_argument("--count", type=int, default=10, help="number of questions (default 10)")
    parser.add_argument("--seed", action="store_true", help="also load the new set into the DB")
    args = parser.parse_args()

    set_id = f"{slugify(args.topic)}-l{args.level}"
    output_path = DATA_DIR / f"{set_id}.json"
    if output_path.exists():
        print(f"Refusing to overwrite existing set {output_path.name}; delete it first.")
        return 1

    print(f"Generating {args.count} level-{args.level} questions on {args.topic!r} ({MODEL})…")
    data = generate(args.topic, args.track, args.level, args.count, set_id)

    output_path.write_text(
        json.dumps(data.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {output_path} ({len(data.questions)} questions).")

    if args.seed:
        from app.db import get_session_factory, init_db
        from app.services.question_sets import upsert_question_set

        init_db()
        with get_session_factory()() as session:
            upsert_question_set(session, data)
        print("Loaded into the database.")
    else:
        print("Load it with: python scripts/seed.py " + str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
