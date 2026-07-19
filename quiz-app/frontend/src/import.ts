/**
 * Import view: paste any question-set JSON (same schema as
 * data/question_sets/*.json) and load it without redeploying.
 */

import { api, ApiError } from "./api";
import { el, render } from "./dom";

export function showImport(): void {
  const textarea = el("textarea", { className: "import-box" });
  textarea.placeholder = '{\n  "id": "my-set", "title": "…", "track": "ai-engineer", "level": 3,\n  "questions": [ … ]\n}';
  const status = el("div", {});

  const importButton = el(
    "button",
    {
      onClick: () => {
        void (async () => {
          status.replaceChildren();
          let parsed: unknown;
          try {
            parsed = JSON.parse(textarea.value);
          } catch {
            status.replaceChildren(el("div", { className: "error-banner" }, "Not valid JSON."));
            return;
          }
          try {
            const summary = await api.importSet(parsed);
            status.replaceChildren(
              el(
                "div",
                { className: "summary-card" },
                `Imported "${summary.title}" — ${summary.question_count} questions, ` +
                  `track ${summary.track}, level ${summary.level}. It is now live on the dashboard.`,
              ),
            );
          } catch (error) {
            status.replaceChildren(
              el(
                "div",
                { className: "error-banner" },
                error instanceof ApiError ? `Rejected by the server: ${error.message}` : "Network error.",
              ),
            );
          }
        })();
      },
    },
    "Validate & import",
  );

  render(
    el("h1", {}, "Import a question set"),
    el(
      "p",
      { className: "hint" },
      "Paste a question-set JSON produced by scripts/generate_questions.py, the quiz-forge skill, " +
        "or written by hand. The server validates it against the shared schema before loading.",
    ),
    textarea,
    el("div", { className: "card-actions" }, importButton),
    status,
  );
}
