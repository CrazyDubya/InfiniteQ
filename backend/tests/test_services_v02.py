"""
Unit tests for v0.2 service enhancements.

Tests individual service methods without full API integration.
"""
import pytest
from backend.app.models.schema import (
    ProjectProfile,
    PersonaProfile,
    ThreadType,
    PlanNote,
    Phase,
    CoverageMap,
    PhaseCoverageMap,
    Question,
    Answer,
    QuestionOption,
    CoverageKey,
    PlanState,
    ViewProfile,
    ProjectType
)
from backend.app.services.plan_reducer import PlanReducer
from backend.app.services.plan_synthesizer import PlanSynthesizer
from unittest.mock import Mock


class TestPlanReducerV02:
    """Test Plan Reducer v0.2 enhancements."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = Mock()
        self.mock_registry = Mock()
        self.reducer = PlanReducer(self.mock_client, self.mock_registry)

    def test_extract_notes_context(self):
        """Test extraction of semantic tags from plan notes."""
        notes = [
            PlanNote(
                id="note1",
                thread_id="thread1",
                index_in_thread=0,
                raw="We need HIPAA compliance",
                distilled="Must ensure HIPAA compliance for patient data",
                tags=["constraint:hipaa", "constraint:security"]
            ),
            PlanNote(
                id="note2",
                thread_id="thread1",
                index_in_thread=1,
                raw="Worried about scaling",
                distilled="Scalability concerns for 10k concurrent users",
                tags=["risk:scalability", "insight:traffic_peak"]
            ),
            PlanNote(
                id="note3",
                thread_id="thread1",
                index_in_thread=2,
                raw="Keep UI simple",
                distilled="User prefers minimal, clean interface",
                tags=["preference:simple_ui", "decision:no_complex_features"]
            )
        ]

        context = self.reducer._extract_notes_context(notes)

        # Check structure
        assert "constraints" in context
        assert "risks" in context
        assert "preferences" in context
        assert "decisions" in context
        assert "insights" in context

        # Check constraints extracted
        assert len(context["constraints"]) == 2
        assert any("hipaa" in c["tag"] for c in context["constraints"])

        # Check risks extracted
        assert len(context["risks"]) == 1
        assert "scalability" in context["risks"][0]["tag"]

        # Check preferences and decisions
        assert len(context["preferences"]) == 1
        assert len(context["decisions"]) == 1

    def test_update_phase_coverage(self):
        """Test phase-specific coverage updates."""
        phase_coverage = PhaseCoverageMap()

        # Initially all zeros
        assert phase_coverage.prototype.features == 0.0
        assert phase_coverage.v1.features == 0.0

        # Update prototype phase
        self.reducer._update_phase_coverage(
            phase_coverage=phase_coverage,
            phase=Phase.PROTOTYPE,
            coverage_key="features",
            increment=25.0
        )

        assert phase_coverage.prototype.features == 25.0
        assert phase_coverage.v1.features == 0.0  # Unchanged

        # Update v1 phase
        self.reducer._update_phase_coverage(
            phase_coverage=phase_coverage,
            phase=Phase.V1,
            coverage_key="features",
            increment=40.0
        )

        assert phase_coverage.prototype.features == 25.0
        assert phase_coverage.v1.features == 40.0

        # Test max cap at 100
        self.reducer._update_phase_coverage(
            phase_coverage=phase_coverage,
            phase=Phase.V1,
            coverage_key="features",
            increment=80.0
        )

        assert phase_coverage.v1.features == 100.0  # Capped

    def test_update_coverage_with_phases(self):
        """Test coverage update with phase tracking."""
        coverage = CoverageMap(features=10.0)
        phase_coverage = PhaseCoverageMap()

        questions = [
            Question(
                id="Q1",
                coverage_key=CoverageKey.FEATURES,
                priority=0.9,
                text="What features for v1?",
                options=[QuestionOption(id="A", text="Core", effect="narrow")],
                phase=Phase.V1  # Phase-specific question
            )
        ]

        answers = [
            Answer(
                question_id="Q1",
                choice_id="A",
                free_text="Detailed feature list here with lots of context"
            )
        ]

        updated_coverage = self.reducer.update_coverage(
            coverage=coverage,
            questions=questions,
            answers=answers,
            phase_coverage=phase_coverage
        )

        # Overall coverage increased
        assert updated_coverage.features > 10.0

        # Phase coverage updated
        assert phase_coverage.v1.features > 0.0
        assert phase_coverage.prototype.features == 0.0  # Not targeted


class TestPlanSynthesizerV02:
    """Test Plan Synthesizer v0.2 enhancements."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = Mock()
        self.mock_registry = Mock()
        self.synthesizer = PlanSynthesizer(self.mock_client, self.mock_registry)

    def test_generate_repo_scaffold_python(self):
        """Test repo scaffold generation for Python projects."""
        plan_state = PlanState()
        plan_state.architecture.backend = "FastAPI"
        plan_state.architecture.frontend = "React"
        plan_state.architecture.data = "PostgreSQL"

        project_profile = ProjectProfile(type=ProjectType.SAAS)

        scaffold = self.synthesizer._generate_repo_scaffold(plan_state, project_profile)

        assert scaffold.language == "py"
        assert "fastapi" in scaffold.frameworks
        assert "react" in scaffold.frameworks
        assert "postgres" in scaffold.frameworks

        # Check structure
        assert "backend/" in scaffold.structure
        assert "frontend/" in scaffold.structure

    def test_generate_repo_scaffold_typescript(self):
        """Test repo scaffold generation for TypeScript projects."""
        plan_state = PlanState()
        plan_state.architecture.backend = "Node.js Express"
        plan_state.architecture.frontend = "Next.js"

        project_profile = ProjectProfile()

        scaffold = self.synthesizer._generate_repo_scaffold(plan_state, project_profile)

        assert scaffold.language == "ts"
        assert "src/" in scaffold.structure

    def test_generate_tasks(self):
        """Test task generation from plan state."""
        plan_state = PlanState()
        plan_state.architecture.frontend = "React"
        plan_state.architecture.backend = "FastAPI"

        # Add some features
        from backend.app.models.schema import Feature
        plan_state.features = [
            Feature(title="User authentication", must_have=True, notes="OAuth + JWT"),
            Feature(title="Dashboard", must_have=True, notes="Main UI"),
            Feature(title="Admin panel", must_have=False, notes="Nice to have")
        ]

        project_profile = ProjectProfile()

        tasks = self.synthesizer._generate_tasks(plan_state, project_profile)

        # Should have at least: setup + 2 features + testing
        assert len(tasks) >= 4

        # First task should be setup
        assert tasks[0].title.lower().startswith("set up")
        assert tasks[0].phase == Phase.PROTOTYPE

        # Check tasks have required fields
        for task in tasks:
            assert task.id
            assert task.title
            assert task.phase
            assert task.estimate in ["S", "M", "L", "XL"]
            assert len(task.acceptance_criteria) > 0

    def test_generate_llm_prompts(self):
        """Test LLM prompt generation."""
        plan_state = PlanState()
        plan_state.meta.title = "Healthcare Appointment System"
        plan_state.problem.summary = "Patients need easy way to book appointments"
        plan_state.architecture.frontend = "React"
        plan_state.architecture.backend = "Python FastAPI"

        from backend.app.models.schema import Feature, UserPersona
        plan_state.features = [
            Feature(title="Appointment booking", must_have=True),
            Feature(title="Reminders", must_have=True)
        ]
        plan_state.users = [
            UserPersona(role="Patient", needs=["Easy booking", "Reminders"])
        ]

        from backend.app.models.schema import RepoScaffold
        scaffold = RepoScaffold(
            language="py",
            frameworks=["fastapi", "react"],
            structure={"backend/": ["app.py"], "frontend/": ["src/"]}
        )

        project_profile = ProjectProfile(
            team_size="solo",
            timeline="1-3_months"
        )

        prompts = self.synthesizer._generate_llm_prompts(
            plan_state, scaffold, project_profile
        )

        # Should have at least 1 prompt
        assert len(prompts) >= 1

        # Check prompt structure
        prompt = prompts[0]
        assert prompt.id
        assert prompt.title
        assert prompt.target in ["claudecode", "cursor", "windsurf"]
        assert len(prompt.prompt) > 100  # Substantial

        # Check context included
        assert "Healthcare Appointment System" in prompt.prompt
        assert "FastAPI" in prompt.prompt or "React" in prompt.prompt

    def test_format_structure(self):
        """Test structure formatting for readability."""
        structure = {
            "backend/": ["app.py", "models/", "services/"],
            "frontend/": ["src/", "public/"],
            "": ["README.md", ".gitignore"]
        }

        formatted = self.synthesizer._format_structure(structure)

        assert "backend/" in formatted
        assert "app.py" in formatted
        assert "README.md" in formatted

    def test_format_users(self):
        """Test user persona formatting."""
        from backend.app.models.schema import UserPersona

        users = [
            UserPersona(
                role="Admin",
                needs=["Manage users", "View analytics"]
            ),
            UserPersona(
                role="Customer",
                needs=["Browse products", "Make purchases"]
            )
        ]

        formatted = self.synthesizer._format_users(users)

        assert "Admin" in formatted
        assert "Customer" in formatted
        assert "Manage users" in formatted
        assert "Browse products" in formatted


class TestProfileIntegration:
    """Test how profiles integrate across services."""

    def test_project_profile_defaults(self):
        """Test project profile has sensible defaults."""
        profile = ProjectProfile()

        assert profile.type == ProjectType.SAAS
        assert profile.sophistication == "mvp"
        assert profile.team_size == "solo"
        assert profile.timeline == "1-4_weeks"
        assert isinstance(profile.tech_constraints, list)
        assert isinstance(profile.non_goals, list)

    def test_persona_profile_defaults(self):
        """Test persona profile has sensible defaults."""
        profile = PersonaProfile()

        assert profile.role == PersonaRole.FOUNDER_SOLO
        assert 0 <= profile.tech_comfort <= 10
        assert 0 <= profile.business_comfort <= 10
        assert profile.preferred_depth in ["light", "medium", "deep"]

    def test_thread_types_available(self):
        """Test all thread types are defined."""
        thread_types = [
            ThreadType.KICKOFF,
            ThreadType.ARCHITECTURE,
            ThreadType.PRODUCT_UX,
            ThreadType.DATA_ML,
            ThreadType.OPS_INFRA,
            ThreadType.RISK,
            ThreadType.GTM,
            ThreadType.SANITY_CHECK,
            ThreadType.CUSTOM
        ]

        assert len(thread_types) == 9

    def test_view_profiles_available(self):
        """Test all view profiles are defined."""
        views = [
            ViewProfile.BUILDER,
            ViewProfile.STAKEHOLDER,
            ViewProfile.INVESTOR,
            ViewProfile.AGENT_SPEC
        ]

        assert len(views) == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
