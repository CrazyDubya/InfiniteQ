"""
Intelligent Execution Bundle Generator: Uses LLM to create project-specific outputs.
Replaces the hardcoded template approach in plan_synthesizer.py.
"""
import logging
from typing import List, Optional
from app.models.schema import (
    PlanState,
    ProjectProfile,
    ExecutionBundle,
    RepoScaffold,
    Task,
    LLMPromptTemplate,
    Phase
)
from app.services.vultr_client import VultrClient
from app.services.model_registry import ModelRegistry

logger = logging.getLogger(__name__)


SCAFFOLD_GENERATION_PROMPT = """You are an expert software architect. Given a project plan, generate a repository structure that perfectly fits the project requirements.

Project Plan:
{plan_json}

Project Profile:
- Type: {project_type}
- Team size: {team_size}
- Timeline: {timeline}
- Tech constraints: {tech_constraints}

Generate a repository scaffold as JSON:
{{
    "language": "py" | "ts" | "go" | "rust" | "java",
    "frameworks": ["framework1", "framework2", ...],
    "structure": {{
        "folder/": ["file1", "subfolder/", "file2"],
        "another_folder/": [...],
        "": ["root_file1", "root_file2"]
    }},
    "reasoning": "Brief explanation of architectural choices"
}}

Requirements:
1. Language and frameworks MUST match the architecture described in the plan
2. Structure MUST include all components mentioned (frontend, backend, data, etc.)
3. Include config files, tests folder, docs folder
4. Use best practices for the chosen stack
5. Keep structure practical for the team size

Output ONLY valid JSON."""


TASK_GENERATION_PROMPT = """You are a technical project manager. Given a project plan, create a phased task breakdown.

Project Plan:
{plan_json}

Features to implement:
{features_json}

Milestones from plan:
{milestones_json}

Project constraints:
- Timeline: {timeline}
- Team size: {team_size}
- Budget: {budget}

Generate tasks as JSON array:
{{
    "tasks": [
        {{
            "id": "TASK_001",
            "title": "Clear task title",
            "phase": "prototype" | "v1" | "scale_up" | "v2_plus",
            "description": "Detailed description of what to build",
            "acceptance_criteria": ["Criterion 1", "Criterion 2", ...],
            "estimate": "S" | "M" | "L",
            "dependencies": ["TASK_ID", ...]
        }}
    ]
}}

Requirements:
1. Create tasks for EVERY feature in the plan, not just 5
2. Phase assignment should match feature priority and milestones
3. Estimates should be realistic for the team size
4. Dependencies should form a valid DAG (no cycles)
5. Include setup, testing, and deployment tasks
6. Acceptance criteria should be specific and testable

Output ONLY valid JSON."""


PROMPT_GENERATION_PROMPT = """You are an expert at writing prompts for AI coding assistants. Given a project plan, create ready-to-use prompts.

Project Plan:
{plan_json}

Repository Structure:
{scaffold_json}

Tasks to complete:
{tasks_json}

Target tool: {target_tool}

Tool-specific guidelines:
- claudecode: Use clear sections, mention /commands like /review, use HEREDOC for multi-line
- cursor: Reference .cursorrules format, use @file mentions, structured code blocks
- windsurf: Focus on step-by-step instructions, clear acceptance criteria
- generic: Universal format, detailed specifications

Generate prompts as JSON:
{{
    "prompts": [
        {{
            "id": "PROMPT_001",
            "title": "Descriptive title",
            "target": "{target_tool}",
            "prompt": "The full prompt text\\n\\nWith multiple sections\\n\\nAnd clear instructions"
        }}
    ]
}}

Requirements:
1. Prompts should include actual project context (not placeholders)
2. Include the specific tech stack and architecture decisions
3. Reference actual features and acceptance criteria from tasks
4. Use tool-specific conventions and formatting
5. Create prompts for: initial setup, each major feature, testing, deployment

Output ONLY valid JSON."""


class IntelligentBundleGenerator:
    """
    Generates execution bundles using LLM instead of templates.
    Creates project-specific scaffolds, tasks, and prompts.
    """

    def __init__(self, vultr_client: VultrClient, model_registry: ModelRegistry):
        """
        Initialize generator.

        Args:
            vultr_client: Vultr API client
            model_registry: Model registry for selecting models
        """
        self.client = vultr_client
        self.registry = model_registry

    def generate_bundle(
        self,
        plan_state: PlanState,
        project_profile: ProjectProfile,
        target_tool: str = "claudecode"
    ) -> ExecutionBundle:
        """
        Generate a complete execution bundle using LLM.

        Args:
            plan_state: The finalized plan state
            project_profile: Project profile for context
            target_tool: Primary AI tool target (claudecode, cursor, windsurf)

        Returns:
            Project-specific execution bundle
        """
        logger.info(f"Generating intelligent execution bundle for {plan_state.meta.title}")

        # Generate scaffold
        scaffold = self._generate_scaffold(plan_state, project_profile)

        # Generate tasks
        tasks = self._generate_tasks(plan_state, project_profile)

        # Generate prompts (using scaffold and tasks for context)
        prompts = self._generate_prompts(plan_state, scaffold, tasks, target_tool)

        return ExecutionBundle(
            repo_scaffold=scaffold,
            tasks=tasks,
            prompts=prompts
        )

    def _generate_scaffold(
        self,
        plan_state: PlanState,
        project_profile: ProjectProfile
    ) -> RepoScaffold:
        """Generate project-specific repository scaffold using LLM."""
        try:
            model = self._get_model("tech")

            prompt = SCAFFOLD_GENERATION_PROMPT.format(
                plan_json=plan_state.model_dump_json(indent=2),
                project_type=project_profile.type.value,
                team_size=project_profile.team_size,
                timeline=project_profile.timeline,
                tech_constraints=", ".join(project_profile.tech_constraints) or "none specified"
            )

            result = self.client.chat_completion_json(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000
            )

            if isinstance(result, dict):
                return RepoScaffold(
                    language=result.get("language", "ts"),
                    frameworks=result.get("frameworks", []),
                    structure=result.get("structure", {})
                )

        except Exception as e:
            logger.error(f"Scaffold generation failed: {e}")

        # Fallback to basic scaffold
        return self._fallback_scaffold(plan_state)

    def _generate_tasks(
        self,
        plan_state: PlanState,
        project_profile: ProjectProfile
    ) -> List[Task]:
        """Generate project-specific task breakdown using LLM."""
        try:
            model = self._get_model("reasoning")

            # Prepare features JSON
            features_json = [
                {"title": f.title, "must_have": f.must_have, "notes": f.notes}
                for f in plan_state.features
            ]

            # Prepare milestones JSON
            milestones_json = [
                {"name": m.name, "duration_weeks": m.duration_weeks, "goals": m.goals}
                for m in plan_state.milestones
            ]

            prompt = TASK_GENERATION_PROMPT.format(
                plan_json=plan_state.model_dump_json(indent=2),
                features_json=str(features_json),
                milestones_json=str(milestones_json),
                timeline=project_profile.timeline,
                team_size=project_profile.team_size,
                budget=project_profile.budget_band
            )

            result = self.client.chat_completion_json(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=4000
            )

            if isinstance(result, dict) and "tasks" in result:
                tasks = []
                for t in result["tasks"]:
                    try:
                        tasks.append(Task(
                            id=t.get("id", f"TASK_{len(tasks)+1:03d}"),
                            title=t.get("title", "Untitled task"),
                            phase=Phase(t.get("phase", "v1")),
                            description=t.get("description", ""),
                            acceptance_criteria=t.get("acceptance_criteria", []),
                            estimate=t.get("estimate", "M"),
                            dependencies=t.get("dependencies", [])
                        ))
                    except Exception as parse_error:
                        logger.warning(f"Failed to parse task: {parse_error}")
                return tasks

        except Exception as e:
            logger.error(f"Task generation failed: {e}")

        # Fallback to basic tasks
        return self._fallback_tasks(plan_state)

    def _generate_prompts(
        self,
        plan_state: PlanState,
        scaffold: RepoScaffold,
        tasks: List[Task],
        target_tool: str
    ) -> List[LLMPromptTemplate]:
        """Generate tool-specific prompts using LLM."""
        try:
            model = self._get_model("synthesis")

            tasks_json = [
                {"id": t.id, "title": t.title, "phase": t.phase.value, "description": t.description}
                for t in tasks[:10]  # Limit for context
            ]

            prompt = PROMPT_GENERATION_PROMPT.format(
                plan_json=plan_state.model_dump_json(indent=2),
                scaffold_json=scaffold.model_dump_json(indent=2),
                tasks_json=str(tasks_json),
                target_tool=target_tool
            )

            result = self.client.chat_completion_json(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=4000
            )

            if isinstance(result, dict) and "prompts" in result:
                prompts = []
                for p in result["prompts"]:
                    try:
                        prompts.append(LLMPromptTemplate(
                            id=p.get("id", f"PROMPT_{len(prompts)+1:03d}"),
                            title=p.get("title", "Untitled prompt"),
                            target=p.get("target", target_tool),
                            prompt=p.get("prompt", "")
                        ))
                    except Exception as parse_error:
                        logger.warning(f"Failed to parse prompt: {parse_error}")
                return prompts

        except Exception as e:
            logger.error(f"Prompt generation failed: {e}")

        # Fallback to basic prompts
        return self._fallback_prompts(plan_state, scaffold, target_tool)

    def _get_model(self, role: str) -> str:
        """Get appropriate model for the role."""
        if role == "tech":
            models = self.registry.pick_tech_models(k=1)
        elif role == "reasoning":
            models = self.registry.pick_reasoning_models(k=1)
        else:
            models = self.registry.pick_synthesis_model()
            if models:
                return models
            models = self.registry.pick_strategy_models(k=1)

        return models[0] if models else "llama-3.3-70b-instruct-fp8"

    def _fallback_scaffold(self, plan_state: PlanState) -> RepoScaffold:
        """Basic scaffold when LLM fails."""
        arch = plan_state.architecture
        tech_stack = f"{arch.frontend} {arch.backend} {arch.data}".lower()

        language = "ts"
        if "python" in tech_stack or "fastapi" in tech_stack:
            language = "py"

        frameworks = []
        for fw in ["react", "fastapi", "django", "express", "next"]:
            if fw in tech_stack:
                frameworks.append(fw)

        return RepoScaffold(
            language=language,
            frameworks=frameworks,
            structure={
                "src/": ["index", "components/", "services/", "utils/"],
                "tests/": ["unit/", "integration/"],
                "docs/": ["README.md"],
                "": ["package.json" if language == "ts" else "requirements.txt", ".gitignore", "README.md"]
            }
        )

    def _fallback_tasks(self, plan_state: PlanState) -> List[Task]:
        """Basic tasks when LLM fails."""
        tasks = [
            Task(
                id="TASK_001",
                title="Project setup and configuration",
                phase=Phase.PROTOTYPE,
                description="Initialize project with dependencies and basic structure",
                acceptance_criteria=["Project runs locally", "All dependencies installed"],
                estimate="S",
                dependencies=[]
            )
        ]

        for i, feature in enumerate(plan_state.features, 2):
            tasks.append(Task(
                id=f"TASK_{i:03d}",
                title=f"Implement {feature.title}",
                phase=Phase.PROTOTYPE if feature.must_have else Phase.V1,
                description=feature.notes or f"Build {feature.title}",
                acceptance_criteria=[f"{feature.title} works as specified"],
                estimate="M",
                dependencies=["TASK_001"]
            ))

        return tasks

    def _fallback_prompts(
        self,
        plan_state: PlanState,
        scaffold: RepoScaffold,
        target_tool: str
    ) -> List[LLMPromptTemplate]:
        """Basic prompts when LLM fails."""
        return [
            LLMPromptTemplate(
                id="PROMPT_001",
                title="Initial project setup",
                target=target_tool,
                prompt=f"""Please set up a new project: {plan_state.meta.title}

Problem: {plan_state.problem.summary}

Tech Stack:
- Language: {scaffold.language}
- Frameworks: {', '.join(scaffold.frameworks)}
- Frontend: {plan_state.architecture.frontend}
- Backend: {plan_state.architecture.backend}

Please initialize the project structure and basic configuration."""
            )
        ]
