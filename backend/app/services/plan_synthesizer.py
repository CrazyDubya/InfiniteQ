"""
Plan Synthesizer: creates final build-ready output.
Version 0.2: Adds view profiles and execution bundle generation.
"""
import logging
from typing import Tuple, Optional, List
from app.models.schema import (
    PlanState,
    IdeaBrief,
    # v0.2 additions
    ViewProfile,
    ExecutionBundle,
    RepoScaffold,
    Task,
    LLMPromptTemplate,
    Phase,
    ProjectProfile,
    PlanChunk,
    Visibility
)
from app.services.vultr_client import VultrClient
from app.services.model_registry import ModelRegistry
from app.prompts.templates import (
    PLAN_SYNTHESIS_SYSTEM,
    format_synthesis_prompt
)

logger = logging.getLogger(__name__)


class PlanSynthesizer:
    """
    Converts the plan state into final deliverables:
    1. Structured JSON plan
    2. Markdown brief for AI coding tools
    """

    def __init__(self, vultr_client: VultrClient, model_registry: ModelRegistry):
        """
        Initialize synthesizer.

        Args:
            vultr_client: Vultr API client
            model_registry: Model registry for selecting models
        """
        self.client = vultr_client
        self.registry = model_registry

    def synthesize(
        self,
        plan_state: PlanState,
        idea_brief: IdeaBrief,
        # v0.2 additions
        view_profile: ViewProfile = ViewProfile.BUILDER,
        project_profile: Optional[ProjectProfile] = None,
        include_execution_bundle: bool = False
    ) -> Tuple[PlanState, str, Optional[ExecutionBundle]]:
        """
        Generate final plan artifacts (v0.2: with views and execution bundles).

        Args:
            plan_state: Current plan state
            idea_brief: Original idea brief
            view_profile: Target audience for the plan
            project_profile: Project profile for context
            include_execution_bundle: Whether to generate execution bundle

        Returns:
            Tuple of (final_json_plan, markdown_brief, execution_bundle)
        """
        try:
            # Use best synthesis model
            model = self.registry.pick_synthesis_model()
            if not model:
                # Fallback to any available model
                models = self.registry.pick_strategy_models(k=1)
                model = models[0] if models else None

            if not model:
                raise ValueError("No synthesis models available")

            logger.info(f"Synthesizing with model: {model} (view: {view_profile.value})")

            user_prompt = format_synthesis_prompt(
                plan_state=plan_state.model_dump(),
                idea_brief=idea_brief.model_dump(),
                # v0.2 additions
                view_profile=view_profile.value,
                project_profile=project_profile.model_dump() if project_profile else None
            )

            messages = [
                {"role": "system", "content": PLAN_SYNTHESIS_SYSTEM},
                {"role": "user", "content": user_prompt}
            ]

            result = self.client.chat_completion_json(
                model=model,
                messages=messages,
                temperature=0.4,
                max_tokens=4000
            )

            # Extract JSON plan and markdown
            if not isinstance(result, dict):
                raise ValueError("Expected dict response")

            json_plan_data = result.get("json_plan", plan_state.model_dump())
            markdown_brief = result.get("markdown_brief", "")

            # Parse JSON plan
            final_plan = PlanState(**json_plan_data)

            if not markdown_brief:
                # Generate fallback markdown
                markdown_brief = self._generate_fallback_markdown(final_plan, idea_brief)

            # v0.2: Generate execution bundle if requested
            execution_bundle = None
            if include_execution_bundle:
                execution_bundle = self._generate_execution_bundle(
                    plan_state=final_plan,
                    project_profile=project_profile or ProjectProfile()
                )

            logger.info("Synthesis completed successfully")
            return final_plan, markdown_brief, execution_bundle

        except Exception as e:
            logger.error(f"Synthesis failed: {e}", exc_info=True)
            # Return best-effort output
            return plan_state, self._generate_fallback_markdown(plan_state, idea_brief), None

    def _generate_fallback_markdown(
        self,
        plan_state: PlanState,
        idea_brief: IdeaBrief
    ) -> str:
        """
        Generate fallback markdown if synthesis fails.

        Args:
            plan_state: Plan state
            idea_brief: Idea brief

        Returns:
            Basic markdown brief
        """
        sections = []

        # Header
        sections.append(f"# {plan_state.meta.title or 'Project Plan'}\n")

        # Problem
        if plan_state.problem.summary:
            sections.append("## Problem & Context\n")
            sections.append(f"{plan_state.problem.summary}\n")
            if plan_state.problem.pain_points:
                sections.append("\n**Pain Points:**")
                for pain in plan_state.problem.pain_points:
                    sections.append(f"- {pain}")
            sections.append("")

        # Users
        if plan_state.users:
            sections.append("## User Personas\n")
            for user in plan_state.users:
                sections.append(f"### {user.role}")
                if user.needs:
                    sections.append("\n**Needs:**")
                    for need in user.needs:
                        sections.append(f"- {need}")
                if user.environment:
                    sections.append(f"\n**Environment:** {user.environment}")
                sections.append("")

        # Features
        if plan_state.features:
            sections.append("## Features & Requirements\n")
            must_have = [f for f in plan_state.features if f.must_have]
            nice_to_have = [f for f in plan_state.features if not f.must_have]

            if must_have:
                sections.append("### Must-Have")
                for feat in must_have:
                    sections.append(f"- **{feat.title}**")
                    if feat.notes:
                        sections.append(f"  - {feat.notes}")
                sections.append("")

            if nice_to_have:
                sections.append("### Nice-to-Have")
                for feat in nice_to_have:
                    sections.append(f"- {feat.title}")
                sections.append("")

        # Architecture
        if plan_state.architecture.frontend or plan_state.architecture.backend:
            sections.append("## Recommended Architecture\n")
            if plan_state.architecture.frontend:
                sections.append(f"**Frontend:** {plan_state.architecture.frontend}\n")
            if plan_state.architecture.backend:
                sections.append(f"**Backend:** {plan_state.architecture.backend}\n")
            if plan_state.architecture.data:
                sections.append(f"**Data:** {plan_state.architecture.data}\n")
            if plan_state.architecture.integrations:
                sections.append("\n**Integrations:**")
                for integration in plan_state.architecture.integrations:
                    sections.append(f"- {integration}")
            sections.append("")

        # Constraints
        if plan_state.constraints.time or plan_state.constraints.budget:
            sections.append("## Constraints\n")
            if plan_state.constraints.time:
                sections.append(f"**Time:** {plan_state.constraints.time}\n")
            if plan_state.constraints.budget:
                sections.append(f"**Budget:** {plan_state.constraints.budget}\n")
            if plan_state.constraints.compliance:
                sections.append("\n**Compliance:**")
                for comp in plan_state.constraints.compliance:
                    sections.append(f"- {comp}")
            sections.append("")

        # Milestones
        if plan_state.milestones:
            sections.append("## Implementation Phases\n")
            for i, milestone in enumerate(plan_state.milestones, 1):
                sections.append(f"### Phase {i}: {milestone.name}")
                if milestone.duration_weeks:
                    sections.append(f"**Duration:** ~{milestone.duration_weeks} weeks\n")
                if milestone.goals:
                    sections.append("**Goals:**")
                    for goal in milestone.goals:
                        sections.append(f"- {goal}")
                sections.append("")

        # Risks
        if plan_state.risks:
            sections.append("## Risks & Mitigation\n")
            for risk in plan_state.risks:
                sections.append(f"**Risk:** {risk.risk}")
                sections.append(f"**Mitigation:** {risk.mitigation}\n")

        # Open Questions
        if plan_state.open_questions:
            sections.append("## Open Questions\n")
            for question in plan_state.open_questions:
                sections.append(f"- {question}")
            sections.append("")

        # Next Steps
        sections.append("## Next Steps for AI Agent\n")
        sections.append("1. Review and validate this plan")
        sections.append("2. Set up project structure and dependencies")
        sections.append("3. Implement core functionality phase by phase")
        sections.append("4. Add tests and documentation")
        sections.append("5. Deploy and iterate based on feedback")

        return "\n".join(sections)

    def _generate_execution_bundle(
        self,
        plan_state: PlanState,
        project_profile: ProjectProfile
    ) -> ExecutionBundle:
        """
        Generate execution bundle with repo scaffold, tasks, and prompts (v0.2).

        Args:
            plan_state: Final plan state
            project_profile: Project profile

        Returns:
            Execution bundle
        """
        # Generate repo scaffold
        repo_scaffold = self._generate_repo_scaffold(plan_state, project_profile)

        # Generate task breakdown
        tasks = self._generate_tasks(plan_state, project_profile)

        # Generate LLM prompts
        prompts = self._generate_llm_prompts(plan_state, repo_scaffold, project_profile)

        return ExecutionBundle(
            repo_scaffold=repo_scaffold,
            tasks=tasks,
            prompts=prompts
        )

    def _generate_repo_scaffold(
        self,
        plan_state: PlanState,
        project_profile: ProjectProfile
    ) -> RepoScaffold:
        """
        Generate repository structure scaffold.

        Args:
            plan_state: Plan state
            project_profile: Project profile

        Returns:
            Repo scaffold
        """
        # Infer language and frameworks from architecture and constraints
        arch = plan_state.architecture
        language = "ts"  # Default

        # Detect language from tech stack
        tech_stack = f"{arch.frontend} {arch.backend} {arch.data}".lower()
        if "python" in tech_stack or "fastapi" in tech_stack or "django" in tech_stack:
            language = "py"
        elif "go" in tech_stack or "golang" in tech_stack:
            language = "go"
        elif "rust" in tech_stack:
            language = "rust"

        # Extract frameworks
        frameworks = []
        if "react" in tech_stack:
            frameworks.append("react")
        if "fastapi" in tech_stack:
            frameworks.append("fastapi")
        if "django" in tech_stack:
            frameworks.append("django")
        if "prisma" in tech_stack:
            frameworks.append("prisma")
        if "postgres" in tech_stack:
            frameworks.append("postgres")

        # Build structure
        structure = {}
        if language == "py":
            structure = {
                "backend/": ["app.py", "models/", "services/", "tests/"],
                "": ["requirements.txt", "README.md", ".gitignore"]
            }
            if "react" in frameworks:
                structure["frontend/"] = ["src/", "public/", "package.json"]
        elif language == "ts":
            structure = {
                "src/": ["index.ts", "types/", "services/", "tests/"],
                "": ["package.json", "tsconfig.json", "README.md", ".gitignore"]
            }
        else:
            # Generic structure
            structure = {
                "src/": ["main", "tests/"],
                "": ["README.md", ".gitignore"]
            }

        return RepoScaffold(
            language=language,
            frameworks=frameworks,
            structure=structure
        )

    def _generate_tasks(
        self,
        plan_state: PlanState,
        project_profile: ProjectProfile
    ) -> List[Task]:
        """
        Generate task breakdown by phase.

        Args:
            plan_state: Plan state
            project_profile: Project profile

        Returns:
            List of tasks
        """
        tasks = []

        # Task 1: Setup
        tasks.append(Task(
            id="TASK_001",
            title="Set up project structure and dependencies",
            phase=Phase.PROTOTYPE,
            description=f"Initialize {plan_state.architecture.frontend or 'frontend'} and {plan_state.architecture.backend or 'backend'} with necessary dependencies.",
            acceptance_criteria=[
                "Project structure matches scaffold",
                "All dependencies installed",
                "Basic health check endpoint works"
            ],
            estimate="S",
            dependencies=[]
        ))

        # Task 2: Core features
        core_features = [f for f in plan_state.features if f.must_have]
        for i, feature in enumerate(core_features[:5], 2):  # Limit to 5 features
            phase = Phase.PROTOTYPE if i <= 3 else Phase.V1
            tasks.append(Task(
                id=f"TASK_{i:03d}",
                title=f"Implement {feature.title}",
                phase=phase,
                description=feature.notes or f"Build {feature.title} functionality",
                acceptance_criteria=[
                    f"{feature.title} works as expected",
                    "Unit tests pass",
                    "Integration with other components verified"
                ],
                estimate="M",
                dependencies=["TASK_001"]
            ))

        # Task: Testing
        tasks.append(Task(
            id=f"TASK_{len(tasks)+1:03d}",
            title="Add comprehensive tests",
            phase=Phase.V1,
            description="Write unit and integration tests for core functionality",
            acceptance_criteria=[
                "Test coverage > 70%",
                "All critical paths tested",
                "CI/CD pipeline passing"
            ],
            estimate="M",
            dependencies=[t.id for t in tasks if t.phase == Phase.PROTOTYPE]
        ))

        return tasks

    def _generate_llm_prompts(
        self,
        plan_state: PlanState,
        repo_scaffold: RepoScaffold,
        project_profile: ProjectProfile
    ) -> List[LLMPromptTemplate]:
        """
        Generate ready-to-use prompts for AI coding tools.

        Args:
            plan_state: Plan state
            repo_scaffold: Repo scaffold
            project_profile: Project profile

        Returns:
            List of prompt templates
        """
        prompts = []

        # Prompt 1: Initial setup for ClaudeCode
        frameworks_str = ", ".join(repo_scaffold.frameworks) if repo_scaffold.frameworks else "the specified stack"
        prompts.append(LLMPromptTemplate(
            id="PROMPT_001",
            title="Initial project setup",
            target="claudecode",
            prompt=f"""Please set up a new project with the following requirements:

**Project:** {plan_state.meta.title}

**Problem:** {plan_state.problem.summary}

**Tech Stack:**
- Frontend: {plan_state.architecture.frontend or 'TBD'}
- Backend: {plan_state.architecture.backend or 'TBD'}
- Database: {plan_state.architecture.data or 'TBD'}
- Frameworks: {frameworks_str}

**Repository Structure:**
{self._format_structure(repo_scaffold.structure)}

**Constraints:**
- Timeline: {project_profile.timeline}
- Team size: {project_profile.team_size}
- Budget: {project_profile.budget_band}

Please:
1. Initialize the project with the structure above
2. Set up all necessary configuration files
3. Install dependencies
4. Create a basic health check endpoint
5. Add a comprehensive README

Let me know when you're done and I'll provide the next steps."""
        ))

        # Prompt 2: Feature implementation for Cursor
        must_have_features = [f for f in plan_state.features if f.must_have]
        if must_have_features:
            features_list = "\n".join([f"- {f.title}: {f.notes or 'Core functionality'}" for f in must_have_features[:5]])
            prompts.append(LLMPromptTemplate(
                id="PROMPT_002",
                title="Implement core features",
                target="cursor",
                prompt=f"""Implement the following core features for {plan_state.meta.title}:

{features_list}

**Architecture Context:**
- Frontend: {plan_state.architecture.frontend}
- Backend: {plan_state.architecture.backend}
- Database: {plan_state.architecture.data}

**User Context:**
{self._format_users(plan_state.users)}

For each feature:
1. Implement the backend API endpoints
2. Create the frontend UI components
3. Add data models/schemas
4. Write basic unit tests
5. Update documentation

Focus on clean, maintainable code that follows best practices."""
            ))

        return prompts

    def _format_structure(self, structure: dict) -> str:
        """Format structure dict as readable tree."""
        lines = []
        for dir_path, items in structure.items():
            if dir_path:
                lines.append(f"{dir_path}")
                for item in items:
                    lines.append(f"  - {item}")
            else:
                for item in items:
                    lines.append(f"- {item}")
        return "\n".join(lines)

    def _format_users(self, users: list) -> str:
        """Format users as readable text."""
        if not users:
            return "No user personas defined"

        lines = []
        for user in users:
            lines.append(f"**{user.role}:**")
            if user.needs:
                lines.append("  Needs: " + ", ".join(user.needs))
        return "\n".join(lines)
