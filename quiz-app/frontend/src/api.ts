/** Typed API client. Every backend call in the app goes through here. */

import type {
  AnswerRequest,
  AnswerResult,
  ExportSummary,
  QuestionSetSummary,
  Session,
  SessionStartRequest,
  TrackProgress,
} from "./types";

/** Error carrying the backend's `detail` message (e.g. "Level 3 is locked …"). */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    detail: string,
  ) {
    super(detail);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body: unknown = await response.json();
      if (body && typeof body === "object" && "detail" in body) {
        detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      // Non-JSON error body; keep the status text.
    }
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<T>;
}

export const api = {
  listSets: () => request<QuestionSetSummary[]>("/api/sets"),
  importSet: (setJson: unknown) =>
    request<QuestionSetSummary>("/api/sets/import", {
      method: "POST",
      body: JSON.stringify(setJson),
    }),
  listTracks: () => request<string[]>("/api/results/tracks"),
  trackProgress: (track: string) =>
    request<TrackProgress>(`/api/results/progress?track=${encodeURIComponent(track)}`),
  exportSummary: () => request<ExportSummary>("/api/results/export"),
  startSession: (body: SessionStartRequest) =>
    request<Session>("/api/quiz/start", { method: "POST", body: JSON.stringify(body) }),
  submitAnswer: (body: AnswerRequest) =>
    request<AnswerResult>("/api/quiz/answer", { method: "POST", body: JSON.stringify(body) }),
  finishSession: (sessionId: string) =>
    request<{ status: string }>(`/api/quiz/${sessionId}/finish`, { method: "POST" }),
};
