/**
 * Frontend types (mirrors backend schema)
 */

export enum CoverageKey {
  PROBLEM = "problem",
  USERS = "users",
  CONSTRAINTS = "constraints",
  FEATURES = "features",
  ARCHITECTURE = "architecture",
  OPERATIONS = "operations",
  RISKS = "risks",
  DELIVERABLES = "deliverables",
}

export interface CoverageMap {
  problem: number;
  users: number;
  constraints: number;
  features: number;
  architecture: number;
  operations: number;
  risks: number;
  deliverables: number;
}

export interface QuestionOption {
  id: string;
  text: string;
  effect: string;
}

export interface Question {
  id: string;
  coverage_key: CoverageKey;
  priority: number;
  text: string;
  options: QuestionOption[];
}

export interface Answer {
  question_id: string;
  choice_id: string;
  free_text?: string;
}

export interface CreateSessionRequest {
  idea: string;
  mode: "software" | "story" | "process" | "other";
}

export interface CreateSessionResponse {
  session_id: string;
  first_questions: Question[];
  coverage: CoverageMap;
}

export interface AnswerRequest {
  answers: Answer[];
}

export interface AnswerResponse {
  next_questions: Question[];
  coverage: CoverageMap;
  plan_preview?: any;
}

export interface FinishResponse {
  json_plan: any;
  markdown_brief: string;
}
