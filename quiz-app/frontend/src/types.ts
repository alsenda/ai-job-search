/**
 * API types — these mirror the Pydantic schemas in app/schemas.py.
 * If you change one side, change the other; the shapes must stay in sync.
 */

export type QuestionType = "mc" | "flashcard";

export type DifficultyTag =
  | "basic"
  | "intermediate"
  | "advanced"
  | "expert"
  | "ultra-expert";

export type TypicalityTag = "staple" | "common" | "occasional" | "curveball";

export type SelfRating = "nailed" | "partial" | "missed";

export interface QuestionTags {
  difficulty: DifficultyTag;
  typicality: TypicalityTag;
  topics: string[];
}

export interface Question {
  id: string;
  set_id: string;
  type: QuestionType;
  topic: string;
  prompt: string;
  options: string[] | null;
  correct_index: number | null;
  answer_notes: string;
  difficulty_rationale: string;
  tags: QuestionTags;
}

export interface QuestionSetSummary {
  id: string;
  title: string;
  track: string;
  level: number;
  description: string | null;
  question_count: number;
}

export interface SessionStartRequest {
  track: string;
  level?: number;
  mode: "level" | "typical-drill" | "custom";
  typicality?: TypicalityTag[];
  limit?: number;
}

export interface Session {
  id: string;
  track: string;
  level: number | null;
  mode: string;
  questions: Question[];
}

export interface AnswerRequest {
  session_id: string;
  question_id: string;
  chosen_index?: number;
  self_rating?: SelfRating;
}

export interface AnswerResult {
  question_id: string;
  score: number;
  correct: boolean;
  correct_index: number | null;
  answer_notes: string;
}

export interface LevelProgress {
  level: number;
  difficulty: DifficultyTag;
  total_questions: number;
  attempted_questions: number;
  accuracy: number | null;
  unlocked: boolean;
  passed: boolean;
}

export interface TrackProgress {
  track: string;
  levels: LevelProgress[];
  highest_unlocked: number;
}

export interface TopicStat {
  topic: string;
  attempts: number;
  accuracy: number;
}

export interface ExportSummary {
  generated_at: string;
  total_answers: number;
  tracks: TrackProgress[];
  weak_topics: TopicStat[];
  strong_topics: TopicStat[];
}
