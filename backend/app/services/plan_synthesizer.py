"""
Plan Synthesizer: creates final build-ready output.
"""
import logging
from typing import Tuple
from app.models.schema import PlanState, IdeaBrief
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
        idea_brief: IdeaBrief
    ) -> Tuple[PlanState, str]:
        """
        Generate final plan artifacts.

        Args:
            plan_state: Current plan state
            idea_brief: Original idea brief

        Returns:
            Tuple of (final_json_plan, markdown_brief)
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

            logger.info(f"Synthesizing with model: {model}")

            user_prompt = format_synthesis_prompt(
                plan_state=plan_state.model_dump(),
                idea_brief=idea_brief.model_dump()
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

            logger.info("Synthesis completed successfully")
            return final_plan, markdown_brief

        except Exception as e:
            logger.error(f"Synthesis failed: {e}", exc_info=True)
            # Return best-effort output
            return plan_state, self._generate_fallback_markdown(plan_state, idea_brief)

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
