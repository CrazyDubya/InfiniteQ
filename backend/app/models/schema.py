"""
Core data models for the InfiniteQ planning harness.
"""
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


class CoverageKey(str, Enum):
    """Dimensions of project understanding we track."""
    PROBLEM = "problem"
    USERS = "users"
    CONSTRAINTS = "constraints"
    FEATURES = "features"
    ARCHITECTURE = "architecture"
    OPERATIONS = "operations"
    RISKS = "risks"
    DELIVERABLES = "deliverables"


class CoverageMap(BaseModel):
    """Coverage scores (0-100) for each dimension."""
    problem: float = 0.0
    users: float = 0.0
    constraints: float = 0.0
    features: float = 0.0
    architecture: float = 0.0
    operations: float = 0.0
    risks: float = 0.0
    deliverables: float = 0.0


class QuestionOption(BaseModel):
    """A single multiple-choice option."""
    id: str
    text: str
    effect: str  # semantic tag like "narrow_scope", "add_analytics", etc.


class Question(BaseModel):
    """A multiple-choice question."""
    id: str
    coverage_key: CoverageKey
    priority: float = Field(ge=0.0, le=1.0, description="0-1 priority score")
    text: str
    options: List[QuestionOption]


class Answer(BaseModel):
    """User's answer to a question."""
    question_id: str
    choice_id: str
    free_text: Optional[str] = None


class QAPair(BaseModel):
    """Question-answer pair for history."""
    question: Question
    answer: Answer


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


class SessionData(BaseModel):
    """Complete session state."""
    session_id: str
    idea_brief: IdeaBrief
    plan_state: PlanState = Field(default_factory=PlanState)
    coverage: CoverageMap = Field(default_factory=CoverageMap)
    qa_history: List[QAPair] = Field(default_factory=list)
    created_at: str
    updated_at: str
    completed: bool = False


# API Request/Response Models

class CreateSessionRequest(BaseModel):
    """Request to create a new session."""
    idea: str
    mode: Literal["software", "story", "process", "other"] = "software"


class CreateSessionResponse(BaseModel):
    """Response from session creation."""
    session_id: str
    first_questions: List[Question]
    coverage: CoverageMap


class AnswerRequest(BaseModel):
    """Request to submit answers."""
    answers: List[Answer]


class AnswerResponse(BaseModel):
    """Response after submitting answers."""
    next_questions: List[Question]
    coverage: CoverageMap
    plan_preview: Optional[Dict[str, Any]] = None


class FinishResponse(BaseModel):
    """Response from finishing the session."""
    json_plan: PlanState
    markdown_brief: str


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
