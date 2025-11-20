"""
Core data models for the InfiniteQ planning harness.
Version 0.2: Adds threads, profiles, phases, and execution bundles.
"""
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================================
# Coverage & Phases (v0.2)
# ============================================================================

class CoverageKey(str, Enum):
    """Dimensions of project understanding we track."""
    PROBLEM = "problem"
    USERS = "users"
    CONSTRAINTS = "constraints"
    FEATURES = "features"
    ARCHITECTURE = "architecture"
    DATA_ML = "data_ml"
    OPERATIONS = "operations"
    RISKS = "risks"
    GTM = "gtm"  # Go-to-market


class Phase(str, Enum):
    """Project lifecycle phases."""
    PROTOTYPE = "prototype"  # v0 / proof of concept
    V1 = "v1"  # First real launch
    SCALE_UP = "scale_up"  # Growing user base
    V2_PLUS = "v2_plus"  # Mature product


class CoverageMap(BaseModel):
    """Coverage scores (0-100) for each dimension."""
    problem: float = 0.0
    users: float = 0.0
    constraints: float = 0.0
    features: float = 0.0
    architecture: float = 0.0
    data_ml: float = 0.0
    operations: float = 0.0
    risks: float = 0.0
    gtm: float = 0.0


class PhaseCoverageMap(BaseModel):
    """Coverage scores by phase."""
    prototype: CoverageMap = Field(default_factory=CoverageMap)
    v1: CoverageMap = Field(default_factory=CoverageMap)
    scale_up: CoverageMap = Field(default_factory=CoverageMap)
    v2_plus: CoverageMap = Field(default_factory=CoverageMap)


# ============================================================================
# Profiles (v0.2)
# ============================================================================

class ProjectType(str, Enum):
    """Types of projects."""
    SAAS = "saas"
    INTERNAL_TOOL = "internal_tool"
    GAME = "game"
    CONTENT_SITE = "content_site"
    RESEARCH = "research"
    AUTOMATION = "automation"
    OTHER = "other"


class ProjectProfile(BaseModel):
    """Profile of the project being planned."""
    type: ProjectType = ProjectType.SAAS
    sophistication: Literal["toy", "mvp", "production"] = "mvp"
    team_size: Literal["solo", "2-3", "4-10", "10+"] = "solo"
    tech_constraints: List[str] = Field(default_factory=list)  # e.g. ["must_be_js_ts", "no_self_hosted_db"]
    timeline: Literal["weekend", "1-4_weeks", "1-3_months", "6+_months"] = "1-4_weeks"
    budget_band: Literal["<1k", "1k-10k", "10k-100k", "100k+"] = "<1k"
    non_goals: List[str] = Field(default_factory=list)  # explicitly out of scope


class PersonaRole(str, Enum):
    """Roles for the person answering questions."""
    FOUNDER_NON_TECHNICAL = "founder_non_technical"
    FOUNDER_TECHNICAL = "founder_technical"
    TECH_LEAD = "tech_lead"
    PM = "pm"
    DOMAIN_EXPERT = "domain_expert"
    HACKER_PLAYING = "hacker_playing"


class PersonaProfile(BaseModel):
    """Profile of the person answering questions."""
    role: PersonaRole = PersonaRole.FOUNDER_TECHNICAL
    comfort_with_tech: Literal["low", "medium", "high"] = "medium"
    comfort_with_business: Literal["low", "medium", "high"] = "medium"
    preferred_depth: Literal["light", "balanced", "deep"] = "balanced"


# ============================================================================
# Questions & Answers
# ============================================================================

class QuestionOption(BaseModel):
    """A single multiple-choice option."""
    id: str
    text: str
    effect: str  # semantic tag like "narrow_scope", "add_analytics", etc.


class Question(BaseModel):
    """A multiple-choice question (v0.2: adds phase and kind)."""
    id: str
    coverage_key: CoverageKey
    phase: Optional[Phase] = None  # Which phase this question targets
    priority: float = Field(ge=0.0, le=1.0, description="0-1 priority score")
    kind: Literal["multiple_choice", "reflection"] = "multiple_choice"
    text: str
    options: List[QuestionOption] = Field(default_factory=list)  # Empty for reflection questions


class Answer(BaseModel):
    """User's answer to a question."""
    question_id: str
    choice_id: str
    free_text: Optional[str] = None


class QAPair(BaseModel):
    """Question-answer pair for history."""
    question: Question
    answer: Answer


# ============================================================================
# Threads & Modes (v0.2)
# ============================================================================

class ThreadType(str, Enum):
    """Types of interview threads."""
    KICKOFF = "kickoff"
    ARCHITECTURE = "architecture"
    PRODUCT_UX = "product_ux"
    DATA_ML = "data_ml"
    OPS_INFRA = "ops_infra"
    RISK = "risk"
    GTM = "gtm"  # Go-to-market
    SANITY_CHECK = "sanity_check"
    CUSTOM = "custom"


class Mode(str, Enum):
    """Interview modes."""
    KICKOFF = "kickoff"  # Broad initial coverage
    DEEP_DIVE = "deep_dive"  # Focus on specific thread
    SANITY_CHECK = "sanity_check"  # Review existing plan


class PlanNote(BaseModel):
    """A reflection note from the user."""
    id: str
    thread_id: str
    index_in_thread: int  # Question index when note was created
    raw: str  # User's freeform reflection
    distilled: str  # LLM summary
    tags: List[str] = Field(default_factory=list)  # e.g. ["constraint:time_weekends", "risk:scope_creep"]


class ThreadState(BaseModel):
    """State for a single thread within a session."""
    id: str
    session_id: str
    type: ThreadType
    title: str  # "Architecture: Core services"
    root_prompt: str = ""  # Initial description for this thread
    coverage: CoverageMap = Field(default_factory=CoverageMap)
    phase_coverage: PhaseCoverageMap = Field(default_factory=PhaseCoverageMap)
    questions_asked: int = 0
    questions_since_reflection: int = 0
    qa_history: List[QAPair] = Field(default_factory=list)
    notes: List[PlanNote] = Field(default_factory=list)
    created_at: str
    last_updated: str
    active: bool = True  # Can be marked inactive/parked


# Plan State Models

class PlanMeta(BaseModel):
    """Metadata about the project."""
    title: str = ""
    type: str = ""  # software, story, process, research, etc.
    priority: str = ""
    owner: str = ""


class ProblemStatement(BaseModel):
    """The problem being solved."""
    summary: str = ""
    pain_points: List[str] = Field(default_factory=list)


class UserPersona(BaseModel):
    """A user type/persona."""
    role: str = ""
    needs: List[str] = Field(default_factory=list)
    environment: str = ""


class Constraints(BaseModel):
    """Project constraints."""
    time: str = ""
    budget: str = ""
    compliance: List[str] = Field(default_factory=list)
    technical: List[str] = Field(default_factory=list)


class Feature(BaseModel):
    """A feature or requirement."""
    id: str
    title: str
    must_have: bool = True
    notes: str = ""


class Architecture(BaseModel):
    """Technical architecture."""
    frontend: str = ""
    backend: str = ""
    data: str = ""
    integrations: List[str] = Field(default_factory=list)
    infrastructure: str = ""


class Milestone(BaseModel):
    """A project milestone/phase."""
    name: str
    duration_weeks: int = 0
    goals: List[str] = Field(default_factory=list)


class Risk(BaseModel):
    """A project risk."""
    risk: str
    mitigation: str


class PlanState(BaseModel):
    """The canonical JSON plan state."""
    meta: PlanMeta = Field(default_factory=PlanMeta)
    problem: ProblemStatement = Field(default_factory=ProblemStatement)
    users: List[UserPersona] = Field(default_factory=list)
    constraints: Constraints = Field(default_factory=Constraints)
    features: List[Feature] = Field(default_factory=list)
    architecture: Architecture = Field(default_factory=Architecture)
    milestones: List[Milestone] = Field(default_factory=list)
    risks: List[Risk] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)


class IdeaBrief(BaseModel):
    """Normalized version of the user's initial idea."""
    raw_input: str
    normalized_summary: str = ""
    inferred_type: str = ""  # software, story, process, etc.
    key_entities: List[str] = Field(default_factory=list)
    initial_scope: str = ""


# ============================================================================
# Views & Sealed Sections (v0.2)
# ============================================================================

class Visibility(str, Enum):
    """Visibility levels for plan chunks."""
    INTERNAL_ONLY = "internal_only"
    TEAM = "team"
    STAKEHOLDER = "stakeholder"
    DECK_FRIENDLY = "deck_friendly"
    AGENT_ONLY = "agent_only"


class PlanChunk(BaseModel):
    """A chunk of the plan with visibility controls."""
    id: str
    type: Literal["assumption", "feature", "risk", "constraint", "note", "phase_plan"]
    content: str  # Plain text or Markdown
    visibility: Visibility = Visibility.TEAM
    parked: bool = False  # Not part of main v0/v1 plan


class ViewProfile(str, Enum):
    """Profiles for different plan views."""
    BUILDER = "builder"  # Full technical details
    STAKEHOLDER = "stakeholder"  # Business-focused
    INVESTOR = "investor"  # Pitch-friendly
    AGENT_SPEC = "agent_spec"  # For AI coding tools


# ============================================================================
# Execution Bundles (v0.2)
# ============================================================================

class RepoScaffold(BaseModel):
    """Repository structure scaffold."""
    language: str  # "ts", "py", etc.
    frameworks: List[str] = Field(default_factory=list)  # ["fastapi", "react", "prisma"]
    structure: Dict[str, List[str]] = Field(default_factory=dict)  # {"backend/": ["app.py", "models/"]}


class Task(BaseModel):
    """A task in the implementation plan."""
    id: str
    title: str
    phase: Phase
    description: str
    acceptance_criteria: List[str] = Field(default_factory=list)
    estimate: Literal["S", "M", "L"] = "M"
    dependencies: List[str] = Field(default_factory=list)  # Task IDs


class LLMPromptTemplate(BaseModel):
    """Ready-to-use prompt for AI coding tools."""
    id: str
    title: str
    target: Literal["cursor", "claudecode", "windsurf", "generic"] = "generic"
    prompt: str  # Multi-line instructions


class ExecutionBundle(BaseModel):
    """Complete execution package."""
    repo_scaffold: RepoScaffold
    tasks: List[Task] = Field(default_factory=list)
    prompts: List[LLMPromptTemplate] = Field(default_factory=list)


class SessionData(BaseModel):
    """Complete session state (v0.2: adds profiles and threads)."""
    session_id: str
    idea_brief: IdeaBrief
    plan_state: PlanState = Field(default_factory=PlanState)
    coverage: CoverageMap = Field(default_factory=CoverageMap)  # Global coverage across all threads
    qa_history: List[QAPair] = Field(default_factory=list)  # Legacy; threads have their own history

    # v0.2 additions
    project_profile: ProjectProfile = Field(default_factory=ProjectProfile)
    persona_profile: PersonaProfile = Field(default_factory=PersonaProfile)
    threads: Dict[str, ThreadState] = Field(default_factory=dict)  # Keyed by thread_id
    active_thread_id: Optional[str] = None
    mode: Mode = Mode.KICKOFF
    plan_chunks: List[PlanChunk] = Field(default_factory=list)  # Structured plan sections with visibility

    created_at: str
    updated_at: str
    completed: bool = False


# ============================================================================
# API Request/Response Models (v0.2)
# ============================================================================

class CreateSessionRequest(BaseModel):
    """Request to create a new session (v0.2: adds profiles)."""
    idea: str
    mode: Mode = Mode.KICKOFF
    project_profile: Optional[ProjectProfile] = None
    persona_profile: Optional[PersonaProfile] = None


class CreateSessionResponse(BaseModel):
    """Response from session creation."""
    session_id: str
    thread_id: str  # Initial thread ID
    first_questions: List[Question]
    coverage: CoverageMap
    project_profile: ProjectProfile
    persona_profile: PersonaProfile


class AnswerRequest(BaseModel):
    """Request to submit answers."""
    answers: List[Answer]


class AnswerResponse(BaseModel):
    """Response after submitting answers."""
    next_questions: List[Question]
    coverage: CoverageMap
    plan_preview: Optional[Dict[str, Any]] = None


class FinishRequest(BaseModel):
    """Request to finish session (v0.2: adds view profile)."""
    view_profile: ViewProfile = ViewProfile.BUILDER
    include_execution_bundle: bool = True


class FinishResponse(BaseModel):
    """Response from finishing the session (v0.2: adds execution bundle)."""
    json_plan: PlanState
    markdown_brief: str
    execution_bundle: Optional[ExecutionBundle] = None
    plan_chunks: List[PlanChunk] = Field(default_factory=list)


# Thread API Models (v0.2)

class CreateThreadRequest(BaseModel):
    """Request to create a new thread."""
    type: ThreadType
    title: str
    root_prompt: str = ""


class CreateThreadResponse(BaseModel):
    """Response from creating a thread."""
    thread: ThreadState
    first_questions: List[Question]


class ListThreadsResponse(BaseModel):
    """Response listing all threads in a session."""
    threads: List[ThreadState]
    active_thread_id: Optional[str] = None


class UpdateThreadRequest(BaseModel):
    """Request to update thread metadata."""
    title: Optional[str] = None
    active: Optional[bool] = None


class ThreadAnswerRequest(BaseModel):
    """Request to submit answers to a thread."""
    answers: List[Answer]


class ThreadAnswerResponse(BaseModel):
    """Response after submitting answers to a thread."""
    next_questions: List[Question]
    thread_coverage: CoverageMap
    phase_coverage: PhaseCoverageMap
    global_coverage: CoverageMap
    reflection_prompt: Optional[Question] = None  # If it's time for reflection


# Model Registry Models

class ModelRole(str, Enum):
    """Roles that different models can play."""
    REASONING = "reasoning"
    CODE_TECH = "code_tech"
    SYNTHESIS = "synthesis"
    STRATEGY = "strategy"
    GENERAL = "general"


class ModelInfo(BaseModel):
    """Information about a Vultr model."""
    id: str
    role: ModelRole
    priority: int = 1  # Higher = preferred within role
