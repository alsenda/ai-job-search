---
name: quiz-forge
description: >
  Generates progressively harder interview-quiz question sets for the quiz-app based on the
  candidate's saved quiz results, targeting weak topics and the next difficulty level.
  Triggers on: /quiz-forge, quiz forge, new quiz questions, harder questions, more questions,
  next level questions, quiz results
allowed-tools: Read, Write, Glob, Grep, Bash, WebFetch, WebSearch
---

# Quiz Forge

---

## Overview

`/quiz-forge` reads the candidate's quiz performance (from the deployed quiz-app or a pasted
results export), identifies weak topics and current mastery per track, and writes a **new
question set JSON** one notch harder than what the candidate has mastered — concentrated on
their weak spots. The set is validated against the app's schema and saved into
`quiz-app/data/question_sets/`, ready to seed or import.

The end goal: by the time the candidate aces every generated set, they should be able to pass
any interview as an AI engineer, tech lead, or developer.

## Invocation

- **`/quiz-forge`** — fetch results from the deployed app (or ask for an export), pick the
  track+level+topics automatically
- **`/quiz-forge <track>`** — restrict to one track (`ai-engineer`, `tech-lead`, `developer`,
  or any custom track present in the data)
- **`/quiz-forge <topic>`** — generate a set on a specific topic (e.g. `/quiz-forge Kubernetes`);
  level is still chosen from results

## Step 1: Load Results

Try these sources in order; use the first that works:

1. **Deployed app**: read `quiz-app/DEPLOYMENT.md` for the production URL (if the file exists)
   and WebFetch `<url>/api/results/export`. The response is JSON matching the `ExportSummary`
   schema in `quiz-app/app/schemas.py`: per-track level progress (accuracy, unlocked, passed)
   plus `weak_topics` and `strong_topics`.
2. **Local app**: if a local server is running, `curl http://127.0.0.1:8000/api/results/export`.
3. **Pasted export**: ask the user to open the app and paste the JSON from `/api/results/export`.
4. **No results at all**: fall back to generating a level-1 or level-2 set on a
   fundamentals topic the seed library does not yet cover, and tell the user results-driven
   targeting will kick in once they have played.

Also read, when populated (both are optional):
- `.claude/skills/job-application-assistant/01-candidate-profile.md` — skip if it still
  contains `[YOUR_NAME]`-style placeholders
- `job_search_tracker.csv` — real tracked jobs bias topic selection toward technologies that
  appear in postings the candidate is actually pursuing

## Step 2: Decide Track, Level, and Topics

1. **Track**: the track with the weakest overall performance, unless the user specified one.
2. **Level**: `highest_unlocked` for that track. If that level is already **passed**
   (accuracy ≥ 80% on ≥ 50% of its questions), target `min(level + 1, 5)`. Once a track's
   level 5 is passed, keep generating fresh level-5 sets on new topics — mastery is maintained,
   not finished.
3. **Topics**: take the 3-5 `weak_topics` with the lowest accuracy that belong to this track's
   domain. Blend in topics from tracked job postings when available. If the user named a topic,
   use it.

Print a short plan before generating, e.g.:
> Targeting **ai-engineer level 4** (level 3 passed at 87%). Weak topics: evals (55%),
> serving (60%), agents (68%). Generating 10 questions.

## Step 3: Generate the Question Set

Two equivalent paths — pick based on what is available:

### Path A — the admin script (needs `ANTHROPIC_API_KEY`)
```bash
cd quiz-app && python scripts/generate_questions.py \
  --topic "<topic focus>" --track <track> --level <N> --count 10
```

### Path B — author directly (no API key needed)
Write the set yourself following the schema contract in `quiz-app/app/schemas.py`
(`QuestionSetFile`). Study 2-3 existing sets in `quiz-app/data/question_sets/` first to match
the established quality bar. Rules:

- `id`: `<topic-slug>-l<level>` (must not collide with an existing file); `track` and `level`
  set from Step 2; difficulty tag matching the level
  (1=basic, 2=intermediate, 3=advanced, 4=expert, 5=ultra-expert)
- 8-10 questions, mixing `mc` (auto-graded, 3-5 options, distractors built from real
  misconceptions) and `flashcard` (open questions answered verbally in interviews).
  Levels 4-5 lean toward flashcards
- Every question must be phrased the way interviewers actually ask it, with an honest
  `typicality` tag: `staple` / `common` / `occasional` / `curveball`
- `answer_notes` teach the answer plus what earns bonus credit; `difficulty_rationale`
  justifies the level in one sentence
- **Never repeat or trivially rephrase a prompt from any existing set** — grep
  `quiz-app/data/question_sets/` before writing
- Concentrate ~70% of questions on the weak topics from Step 2; the rest can extend range
- For fast-moving topics (LLM tooling, frameworks), optionally WebSearch with the current year
  to keep questions from going stale — never invent facts

## Step 4: Validate

Always validate before presenting — this is mandatory for both paths:

```bash
cd quiz-app && python scripts/seed.py --validate data/question_sets/<new-file>.json
```

If validation fails, fix the file and re-run until it passes.

## Step 5: Deliver

1. Confirm the file is saved in `quiz-app/data/question_sets/`.
2. Tell the user how to get it into the app, both ways:
   - **Redeploy/seed**: commit + push; on the deployed app run the seed step
     (or locally `python scripts/seed.py`)
   - **No redeploy**: open the app's **Import set** page and paste the JSON — the running app
     validates and loads it immediately
3. Summarize: track, level, topic focus, question count, typicality mix, and which weak
   topics it targets.

## Important Rules

1. **One notch harder, never more.** The set targets the frontier of the candidate's ability —
   the next unlocked/unpassed level — not an arbitrary jump.
2. **Weak spots first.** Results-driven topic selection is the point of this skill; only
   ignore it when the user explicitly names a topic.
3. **Never duplicate prompts.** Check existing sets every time.
4. **Always validate with seed.py before presenting.** A set that fails schema validation is
   not a deliverable.
5. **Be honest with typicality tags.** Do not label a curveball as a staple to make the set
   look more relevant.
6. **Do not edit existing sets** when generating new ones — history and results reference them.
