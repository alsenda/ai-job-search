/**
 * Dashboard view: one panel per track with the five-level ladder, study
 * buttons, the typical-interview drill, and weak/strong topic lists.
 */

import { api, ApiError } from "./api";
import { el, render } from "./dom";
import { startQuiz } from "./quiz";
import type { ExportSummary, LevelProgress, TrackProgress } from "./types";

export async function showDashboard(): Promise<void> {
  render(el("p", { className: "hint" }, "Loading…"));
  let tracks: string[];
  let summary: ExportSummary;
  try {
    [tracks, summary] = await Promise.all([api.listTracks(), api.exportSummary()]);
  } catch (error) {
    render(
      el(
        "div",
        { className: "error-banner" },
        error instanceof ApiError
          ? error.message
          : "Could not reach the server. Start it with: uvicorn app.main:app",
      ),
    );
    return;
  }
  if (tracks.length === 0) {
    render(
      el(
        "div",
        { className: "summary-card" },
        el("h1", {}, "No question sets loaded yet"),
        el(
          "p",
          { className: "hint" },
          "Seed the bundled sets with `python scripts/seed.py`, or paste any set on the Import page.",
        ),
      ),
    );
    return;
  }

  const progresses = await Promise.all(tracks.map((track) => api.trackProgress(track)));
  render(
    ...progresses.map(trackPanel),
    topicsSection(summary),
  );
}

function levelChip(track: string, progress: LevelProgress): HTMLElement {
  const accuracy =
    progress.accuracy === null ? "—" : `${Math.round(progress.accuracy * 100)}%`;
  const chip = el(
    "div",
    { className: `level-chip ${progress.unlocked ? "unlocked" : "locked"}` },
    el(
      "div",
      { className: "level-name" },
      `L${progress.level} · ${progress.difficulty}${progress.passed ? " " : ""}`,
      progress.passed ? el("span", { className: "passed" }, "✓ passed") : "",
    ),
    el(
      "div",
      { className: "level-meta" },
      progress.unlocked
        ? `${progress.attempted_questions}/${progress.total_questions} tried · ${accuracy}`
        : "🔒 pass the previous level",
    ),
  );
  const meterFill = el("div", {});
  meterFill.style.width = `${Math.round((progress.accuracy ?? 0) * 100)}%`;
  chip.append(el("div", { className: "meter" }, meterFill));
  if (progress.unlocked && progress.total_questions > 0) {
    chip.append(
      el(
        "button",
        {
          className: "ghost",
          onClick: () => {
            void startQuiz({ track, level: progress.level, mode: "level" });
          },
        },
        "Study",
      ),
    );
  }
  return chip;
}

function trackPanel(progress: TrackProgress): HTMLElement {
  return el(
    "div",
    { className: "track-panel" },
    el("h2", {}, progress.track.replace(/-/g, " ")),
    el("div", { className: "levels" }, ...progress.levels.map((lp) => levelChip(progress.track, lp))),
    el(
      "div",
      { className: "track-actions" },
      el(
        "button",
        {
          onClick: () => {
            void startQuiz({
              track: progress.track,
              mode: "typical-drill",
              typicality: ["staple", "common"],
            });
          },
          title: "Only the questions interviewers actually ask (staple + common), across all levels",
        },
        "🎯 Typical interview drill",
      ),
      el(
        "button",
        {
          className: "ghost",
          onClick: () => {
            void startQuiz({ track: progress.track, mode: "custom", limit: 15 });
          },
          title: "Weakest cards first, any level, any typicality",
        },
        "Weak-spot mix",
      ),
    ),
  );
}

function topicsSection(summary: ExportSummary): HTMLElement {
  const list = (title: string, topics: ExportSummary["weak_topics"]) =>
    el(
      "div",
      {},
      el("h3", {}, title),
      topics.length
        ? el(
            "ul",
            {},
            ...topics.map((t) =>
              el(
                "li",
                {},
                el("span", {}, t.topic),
                el("span", {}, `${Math.round(t.accuracy * 100)}% (${t.attempts})`),
              ),
            ),
          )
        : el("p", { className: "hint" }, "Answer a few cards to populate this."),
    );
  return el(
    "div",
    { className: "track-panel topics" },
    list("Weakest topics", summary.weak_topics),
    list("Strongest topics", summary.strong_topics),
  );
}
