/**
 * Quiz view: runs one session as a sequence of flip cards.
 *
 * Multiple choice: pick an option → answer is graded by the API → card flips
 * to show the verdict and explanation.
 * Flashcard: flip to reveal the model answer, then honestly self-rate
 * (nailed / partial / missed) — the rating is what gets scored.
 */

import { api, ApiError } from "./api";
import { el, render } from "./dom";
import type { AnswerResult, Question, Session, SelfRating, SessionStartRequest } from "./types";

interface SessionOutcome {
  question: Question;
  result: AnswerResult;
}

export async function startQuiz(request: SessionStartRequest): Promise<void> {
  let session: Session;
  try {
    session = await api.startSession(request);
  } catch (error) {
    const message =
      error instanceof ApiError ? error.message : "Could not reach the server. Is it running?";
    render(el("div", { className: "error-banner" }, message));
    return;
  }
  runSession(session);
}

function runSession(session: Session): void {
  const outcomes: SessionOutcome[] = [];
  showCard(session, 0, outcomes);
}

function tagChips(question: Question): HTMLElement {
  const chips = el("div", {});
  chips.append(el("span", { className: "tag" }, question.tags.difficulty));
  chips.append(
    el(
      "span",
      { className: `tag typicality-${question.tags.typicality}` },
      `${question.tags.typicality} interview question`,
    ),
  );
  for (const topic of question.tags.topics) {
    chips.append(el("span", { className: "tag" }, topic));
  }
  return chips;
}

function showCard(session: Session, index: number, outcomes: SessionOutcome[]): void {
  const question = session.questions[index];
  if (!question) {
    void showSummary(session, outcomes);
    return;
  }

  const back = el("div", { className: "card-face back" });
  const card = el("div", { className: "card" });

  const front = el(
    "div",
    { className: "card-face front" },
    tagChips(question),
    el("div", { className: "prompt" }, question.prompt),
  );

  const submit = async (answer: { chosen_index?: number; self_rating?: SelfRating }) => {
    try {
      return await api.submitAnswer({
        session_id: session.id,
        question_id: question.id,
        ...answer,
      });
    } catch (error) {
      render(
        el(
          "div",
          { className: "error-banner" },
          error instanceof ApiError ? error.message : "Network error while submitting the answer.",
        ),
      );
      return null;
    }
  };

  const next = () => showCard(session, index + 1, outcomes);

  if (question.type === "mc" && question.options) {
    const optionButtons = question.options.map((option, optionIndex) =>
      el(
        "button",
        {
          onClick: () => {
            void (async () => {
              for (const b of optionButtons) b.disabled = true;
              const result = await submit({ chosen_index: optionIndex });
              if (!result) return;
              outcomes.push({ question, result });
              fillMcBack(back, question, optionIndex, result, next);
              card.classList.add("flipped");
            })();
          },
        },
        `${String.fromCharCode(65 + optionIndex)}. ${option}`,
      ),
    );
    front.append(el("div", { className: "options" }, ...optionButtons));
  } else {
    front.append(
      el(
        "div",
        { className: "card-actions" },
        el(
          "button",
          {
            onClick: () => {
              fillFlashcardBack(back, question, async (rating) => {
                const result = await submit({ self_rating: rating });
                if (!result) return;
                outcomes.push({ question, result });
                next();
              });
              card.classList.add("flipped");
            },
          },
          "Flip card — show model answer",
        ),
      ),
    );
  }

  card.append(front, back);
  render(
    el(
      "div",
      { className: "quiz-header" },
      el("span", {}, `${session.track} — ${session.mode}${session.level ? ` L${session.level}` : ""}`),
      el("span", {}, `Card ${index + 1} / ${session.questions.length}`),
    ),
    el("div", { className: "card-scene" }, card),
  );
}

function fillMcBack(
  back: HTMLElement,
  question: Question,
  chosenIndex: number,
  result: AnswerResult,
  next: () => void,
): void {
  const options = question.options ?? [];
  const correctText =
    result.correct_index !== null ? options[result.correct_index] ?? "" : "";
  back.replaceChildren(
    el(
      "div",
      { className: `verdict ${result.correct ? "good" : "bad"}` },
      result.correct ? "✓ Correct" : "✗ Not quite",
    ),
    el(
      "div",
      { className: "answer-notes" },
      result.correct
        ? ""
        : `You picked: ${options[chosenIndex] ?? ""}\nCorrect answer: ${correctText}\n\n`,
      result.answer_notes,
    ),
    el("div", { className: "rationale" }, `Why this difficulty: ${question.difficulty_rationale}`),
    el("div", { className: "card-actions" }, el("button", { onClick: next }, "Next card →")),
  );
}

function fillFlashcardBack(
  back: HTMLElement,
  question: Question,
  onRate: (rating: SelfRating) => Promise<void>,
): void {
  const ratingButton = (rating: SelfRating, label: string) =>
    el(
      "button",
      {
        className: rating,
        onClick: () => {
          void onRate(rating);
        },
      },
      label,
    );
  back.replaceChildren(
    el("div", { className: "verdict" }, "Model answer"),
    el("div", { className: "answer-notes" }, question.answer_notes),
    el("div", { className: "rationale" }, `Why this difficulty: ${question.difficulty_rationale}`),
    el("div", { className: "hint" }, "How did your spoken answer compare? Be honest — the level gate uses this."),
    el(
      "div",
      { className: "card-actions rating-buttons" },
      ratingButton("nailed", "Nailed it (1.0)"),
      ratingButton("partial", "Partially (0.5)"),
      ratingButton("missed", "Missed it (0)"),
    ),
  );
}

async function showSummary(session: Session, outcomes: SessionOutcome[]): Promise<void> {
  try {
    await api.finishSession(session.id);
  } catch {
    // Summary still renders; the session just stays unfinished server-side.
  }
  const total = outcomes.reduce((sum, o) => sum + o.result.score, 0);
  const pct = outcomes.length ? Math.round((total / outcomes.length) * 100) : 0;
  render(
    el(
      "div",
      { className: "summary-card" },
      el("h1", {}, "Session complete"),
      el("div", { className: "summary-score" }, `${pct}%`),
      el(
        "div",
        { className: "hint" },
        `${total} / ${outcomes.length} points — the level gate needs ≥80% across at least half the level's questions.`,
      ),
      el(
        "ul",
        { className: "summary-list" },
        ...outcomes.map((o) =>
          el(
            "li",
            {},
            `${o.result.score >= 1 ? "✓" : o.result.score > 0 ? "±" : "✗"} [${o.question.topic}] ${o.question.prompt.slice(0, 90)}`,
          ),
        ),
      ),
      el(
        "div",
        { className: "card-actions" },
        el("button", { onClick: () => (window.location.hash = "#/") }, "Back to dashboard"),
      ),
    ),
  );
}
