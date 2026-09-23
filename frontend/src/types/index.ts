/**
 * Frontend types.
 *
 * These mirror the backend Pydantic schema in backend/app/models/schema.py -
 * keep the enum values identical, otherwise the API rejects the request with a
 * 422.
 */

export enum CoverageKey {
  PROBLEM = "problem",
  USERS = "users",
  CONSTRAINTS = "constraints",
  FEATURES = "features",
  ARCHITECTURE = "architecture",
  DATA_ML = "data_ml",
  OPERATIONS = "operations",
  RISKS = "risks",
  GTM = "gtm",
}

export interface CoverageMap {
  problem: number;
  users: number;
  constraints: number;
  features: number;
  architecture: number;
  data_ml: number;
  operations: number;
  risks: number;
  gtm: number;
}

/** Coverage per lifecycle phase. */
export interface PhaseCoverageMap {
  prototype: CoverageMap;
  v1: CoverageMap;
  scale_up: CoverageMap;
  v2_plus: CoverageMap;
}

export enum Phase {
  PROTOTYPE = "prototype",
  V1 = "v1",
  SCALE_UP = "scale_up",
  V2_PLUS = "v2_plus",
}

export interface QuestionOption {
  id: string;
  text: string;
  effect: string;
}

export interface Question {
  id: string;
  coverage_key: CoverageKey;
  phase?: Phase | null;
  priority: number;
  kind?: "multiple_choice" | "reflection";
  text: string;
  options: QuestionOption[];
}

export interface Answer {
  question_id: string;
  choice_id: string;
  free_text?: string;
}

// ============================================================================
// Profiles
// ============================================================================

export enum ProjectType {
  SAAS = "saas",
  INTERNAL_TOOL = "internal_tool",
  GAME = "game",
  CONTENT_SITE = "content_site",
  RESEARCH = "research",
  AUTOMATION = "automation",
  OTHER = "other",
}

export enum PersonaRole {
  FOUNDER_NON_TECHNICAL = "founder_non_technical",
  FOUNDER_TECHNICAL = "founder_technical",
  TECH_LEAD = "tech_lead",
  PM = "pm",
  DOMAIN_EXPERT = "domain_expert",
  HACKER_PLAYING = "hacker_playing",
}

export type ComfortLevel = "low" | "medium" | "high";
export type PreferredDepth = "light" | "balanced" | "deep";

export interface ProjectProfile {
  type?: ProjectType;
  sophistication?: "toy" | "mvp" | "production";
  team_size?: "solo" | "2-3" | "4-10" | "10+";
  tech_constraints?: string[];
  timeline?: "weekend" | "1-4_weeks" | "1-3_months" | "6+_months";
  budget_band?: "<1k" | "1k-10k" | "10k-100k" | "100k+";
  non_goals?: string[];
}

export interface PersonaProfile {
  role?: PersonaRole;
  comfort_with_tech?: ComfortLevel;
  comfort_with_business?: ComfortLevel;
  preferred_depth?: PreferredDepth;
}

// ============================================================================
// Sessions
// ============================================================================

export enum Mode {
  KICKOFF = "kickoff",
  DEEP_DIVE = "deep_dive",
  SANITY_CHECK = "sanity_check",
}

export interface CreateSessionRequest {
  idea: string;
  mode?: Mode;
  project_profile?: ProjectProfile;
  persona_profile?: PersonaProfile;
}

export interface CreateSessionResponse {
  session_id: string;
  thread_id: string;
  first_questions: Question[];
  coverage: CoverageMap;
  project_profile: ProjectProfile;
  persona_profile: PersonaProfile;
}

export interface AnswerRequest {
  answers: Answer[];
}

export interface AnswerResponse {
  next_questions: Question[];
  coverage: CoverageMap;
  plan_preview?: unknown;
}

export interface SessionStatus {
  session_id: string;
  mode: Mode;
  created_at: string;
  updated_at: string;
  completed: boolean;
  qa_count: number;
  coverage: CoverageMap;
  project_profile: ProjectProfile;
  persona_profile: PersonaProfile;
  active_thread_id: string | null;
  thread_count: number;
  threads: {
    id: string;
    title: string;
    type: ThreadType;
    questions_asked: number;
    active: boolean;
    coverage_avg: number;
  }[];
}

// ============================================================================
// Threads & reflections
// ============================================================================

export enum ThreadType {
  KICKOFF = "kickoff",
  ARCHITECTURE = "architecture",
  PRODUCT_UX = "product_ux",
  DATA_ML = "data_ml",
  OPS_INFRA = "ops_infra",
  RISK = "risk",
  GTM = "gtm",
  SANITY_CHECK = "sanity_check",
  CUSTOM = "custom",
}

export interface PlanNote {
  id: string;
  thread_id: string;
  index_in_thread: number;
  raw: string;
  distilled: string;
  tags: string[];
}

export interface ThreadState {
  id: string;
  session_id: string;
  type: ThreadType;
  title: string;
  root_prompt: string;
  coverage: CoverageMap;
  phase_coverage: PhaseCoverageMap;
  questions_asked: number;
  questions_since_reflection: number;
  notes: PlanNote[];
  pending_questions: Question[];
  active: boolean;
  created_at: string;
  last_updated: string;
}

export interface CreateThreadRequest {
  type: ThreadType;
  title: string;
  root_prompt?: string;
}

export interface CreateThreadResponse {
  thread: ThreadState;
  first_questions: Question[];
}

export interface ListThreadsResponse {
  threads: ThreadState[];
  active_thread_id: string | null;
}

export interface UpdateThreadRequest {
  title?: string;
  active?: boolean;
}

export interface ThreadAnswerResponse {
  next_questions: Question[];
  thread_coverage: CoverageMap;
  phase_coverage: PhaseCoverageMap;
  global_coverage: CoverageMap;
  reflection_prompt?: Question | null;
}

export interface SubmitReflectionRequest {
  text: string;
}

export interface SubmitReflectionResponse {
  note: PlanNote;
  message: string;
}

export interface ThreadInsightsResponse {
  thread_id: string;
  note_count: number;
  insights: string;
  notes: PlanNote[];
}

// ============================================================================
// Final plan & execution bundles
// ============================================================================

export enum ViewProfile {
  BUILDER = "builder",
  STAKEHOLDER = "stakeholder",
  INVESTOR = "investor",
  AGENT_SPEC = "agent_spec",
}

export interface PlanChunk {
  id: string;
  type: "assumption" | "feature" | "risk" | "constraint" | "note" | "phase_plan";
  content: string;
  visibility: string;
  parked: boolean;
}

export interface RepoScaffold {
  language: string;
  frameworks: string[];
  structure: Record<string, string[]>;
}

export interface Task {
  id: string;
  title: string;
  phase: Phase;
  description: string;
  acceptance_criteria: string[];
  estimate: "S" | "M" | "L";
  dependencies: string[];
}

export interface LLMPromptTemplate {
  id: string;
  title: string;
  target: "cursor" | "claudecode" | "windsurf" | "generic";
  prompt: string;
}

export interface ExecutionBundle {
  repo_scaffold: RepoScaffold;
  tasks: Task[];
  prompts: LLMPromptTemplate[];
}

export interface FinishRequest {
  view_profile: ViewProfile;
  include_execution_bundle: boolean;
}

export interface FinishResponse {
  json_plan: unknown;
  markdown_brief: string;
  execution_bundle?: ExecutionBundle | null;
  plan_chunks?: PlanChunk[];
}
