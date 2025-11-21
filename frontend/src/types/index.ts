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
  execution_bundle?: ExecutionBundle;
}

// ============================================================================
// v0.2 Types
// ============================================================================

export enum ProjectType {
  SAAS = "saas",
  MOBILE_APP = "mobile_app",
  WEB_APP = "web_app",
  ENTERPRISE = "enterprise",
  ECOMMERCE = "ecommerce",
  ANALYTICS = "analytics",
  DEV_TOOLS = "dev_tools",
  CONTENT = "content",
  OTHER = "other",
}

export enum PersonaRole {
  FOUNDER_SOLO = "founder_solo",
  FOUNDER_TEAM = "founder_team",
  TECH_LEAD = "tech_lead",
  PRODUCT_MANAGER = "product_manager",
  BUSINESS_LEADER = "business_leader",
  ENGINEER = "engineer",
  DESIGNER = "designer",
  OTHER = "other",
}

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

export enum Mode {
  KICKOFF = "kickoff",
  DEEP_DIVE = "deep_dive",
  SANITY_CHECK = "sanity_check",
}

export enum ViewProfile {
  BUILDER = "builder",
  STAKEHOLDER = "stakeholder",
  INVESTOR = "investor",
  AGENT_SPEC = "agent_spec",
}

export enum Phase {
  PROTOTYPE = "prototype",
  V1 = "v1",
  SCALE_UP = "scale_up",
  V2_PLUS = "v2_plus",
}

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
  tech_comfort?: number; // 1-10
  business_comfort?: number; // 1-10
  preferred_depth?: "light" | "medium" | "deep";
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
  questions_asked: number;
  notes: PlanNote[];
}

export interface CreateSessionRequestV2 {
  idea: string;
  mode?: Mode;
  project_profile?: ProjectProfile;
  persona_profile?: PersonaProfile;
}

export interface CreateSessionResponseV2 {
  session_id: string;
  thread_id: string;
  first_questions: Question[];
  coverage: CoverageMap;
  project_profile: ProjectProfile;
  persona_profile: PersonaProfile;
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
  active_thread_id: string;
}

export interface SubmitReflectionRequest {
  reflection: string;
}

export interface SubmitReflectionResponse {
  note: PlanNote;
}

export interface FinishRequestV2 {
  view_profile: ViewProfile;
  include_execution_bundle: boolean;
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
  estimate: "S" | "M" | "L" | "XL";
  dependencies: string[];
}

export interface LLMPromptTemplate {
  id: string;
  title: string;
  target: string;
  prompt: string;
}

export interface ExecutionBundle {
  repo_scaffold: RepoScaffold;
  tasks: Task[];
  prompts: LLMPromptTemplate[];
}
