"""
Reflection Service: handles reflection pulses and PlanNote distillation.
Version 0.2: Captures tacit knowledge through periodic freeform reflections.
"""
import uuid
import logging
from typing import List, Optional
from app.models.schema import (
    Question,
    QuestionOption,
    PlanNote,
    ThreadState,
    ThreadType,
    CoverageKey,
    Phase
)
from app.services.vultr_client import VultrClient
from app.services.model_registry import ModelRegistry

logger = logging.getLogger(__name__)


# Reflection distillation prompt
REFLECTION_DISTILLATION_SYSTEM = """You are a project planning expert who extracts actionable insights from user reflections.

Given a user's freeform reflection about their project, you must:
1. Summarize the key insight in 1-2 concise sentences
2. Extract semantic tags that capture constraints, risks, preferences, or decisions

Tags should follow these patterns:
- "constraint:{type}" - e.g., "constraint:time_weekends_only", "constraint:no_cloud_costs"
- "risk:{type}" - e.g., "risk:scope_creep", "risk:technical_uncertainty"
- "preference:{type}" - e.g., "preference:simple_over_fancy", "preference:open_source"
- "decision:{type}" - e.g., "decision:mvp_first", "decision:skip_auth_for_v1"
- "insight:{type}" - e.g., "insight:user_workflow", "insight:market_timing"

Output JSON format:
{
  "distilled": "One or two sentence summary of the key insight",
  "tags": ["tag1", "tag2", "tag3"]
}

Be concise but capture the essence. Tags should be actionable for planning.
Output ONLY valid JSON, no markdown formatting or additional text."""


class ReflectionService:
    """
    Manages reflection pulses and distills user reflections into PlanNotes.
    """

    def __init__(self, vultr_client: VultrClient, model_registry: ModelRegistry):
        """
        Initialize reflection service.

        Args:
            vultr_client: Vultr API client
            model_registry: Model registry for selecting models
        """
        self.client = vultr_client
        self.registry = model_registry

    def generate_reflection_question(
        self,
        thread: ThreadState,
        project_context: str = ""
    ) -> Question:
        """
        Generate a reflection question for a thread.

        Args:
            thread: Thread state
            project_context: Brief project context

        Returns:
            Reflection question
        """
        question_id = f"REFLECT_{thread.id}_{thread.questions_asked}"

        # Tailor the reflection prompt to the thread type
        reflection_prompts = {
            ThreadType.KICKOFF: "What's the most important thing we haven't talked about yet?",
            ThreadType.ARCHITECTURE: "What technical nuance or constraint are we missing in the architecture discussion?",
            ThreadType.PRODUCT_UX: "What user need or workflow detail should we be more careful about?",
            ThreadType.DATA_ML: "What data challenge or model assumption deserves more attention?",
            ThreadType.OPS_INFRA: "What operational reality or deployment constraint should we consider?",
            ThreadType.RISK: "What risk or failure mode are we underestimating?",
            ThreadType.GTM: "What market or customer insight should shape our go-to-market approach?",
            ThreadType.SANITY_CHECK: "What assumption or gap in this plan makes you most uncomfortable?",
            ThreadType.CUSTOM: "In your own words, what important detail are we missing?"
        }

        prompt_text = reflection_prompts.get(
            thread.type,
            "In your own words, what important detail or nuance are we missing?"
        )

        # Add context if available
        if project_context:
            prompt_text = f"{prompt_text}\n\n(Context: {project_context[:200]}...)"

        return Question(
            id=question_id,
            coverage_key=CoverageKey.RISKS,  # Reflections often surface risks
            phase=None,  # Reflections are phase-agnostic
            priority=1.0,  # Always high priority
            kind="reflection",
            text=prompt_text,
            options=[]  # No options for freeform reflection
        )

    def distill_reflection(
        self,
        raw_reflection: str,
        thread_type: ThreadType,
        project_profile: Optional[dict] = None
    ) -> tuple[str, List[str]]:
        """
        Distill a user's reflection into a summary and tags.

        Args:
            raw_reflection: User's freeform reflection text
            thread_type: Type of thread
            project_profile: Optional project profile context

        Returns:
            Tuple of (distilled_summary, tags)
        """
        try:
            # Select a reasoning model for distillation
            models = self.registry.pick_reasoning_models(k=1)
            if not models:
                logger.warning("No reasoning models available, using fallback distillation")
                return self._fallback_distill(raw_reflection)

            model = models[0]

            # Prepare context
            context = {
                "raw": raw_reflection,
                "thread_type": thread_type.value,
            }
            if project_profile:
                context["project_profile"] = project_profile

            import json
            user_prompt = json.dumps(context, indent=2)

            messages = [
                {"role": "system", "content": REFLECTION_DISTILLATION_SYSTEM},
                {"role": "user", "content": user_prompt}
            ]

            result = self.client.chat_completion_json(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=500
            )

            distilled = result.get("distilled", raw_reflection[:200])
            tags = result.get("tags", [])

            logger.info(f"Distilled reflection: {len(tags)} tags extracted")
            return distilled, tags

        except Exception as e:
            logger.error(f"Reflection distillation failed: {e}", exc_info=True)
            return self._fallback_distill(raw_reflection)

    def _fallback_distill(self, raw_reflection: str) -> tuple[str, List[str]]:
        """
        Fallback distillation when LLM is unavailable.

        Args:
            raw_reflection: Raw reflection text

        Returns:
            Tuple of (distilled_summary, tags)
        """
        # Simple fallback: truncate and extract basic tags
        distilled = raw_reflection[:200]
        if len(raw_reflection) > 200:
            distilled += "..."

        # Basic keyword extraction
        tags = []
        keywords = {
            "time": "constraint:time",
            "weekend": "constraint:time_weekends",
            "budget": "constraint:budget",
            "cost": "constraint:budget",
            "risk": "risk:general",
            "worry": "risk:general",
            "concern": "risk:general",
            "simple": "preference:simplicity",
            "complex": "insight:complexity",
            "user": "insight:user_workflow",
            "customer": "insight:user_workflow",
        }

        raw_lower = raw_reflection.lower()
        for keyword, tag in keywords.items():
            if keyword in raw_lower and tag not in tags:
                tags.append(tag)

        return distilled, tags[:5]  # Max 5 tags

    def create_plan_note(
        self,
        thread_id: str,
        index_in_thread: int,
        raw_reflection: str,
        thread_type: ThreadType,
        project_profile: Optional[dict] = None
    ) -> PlanNote:
        """
        Create a PlanNote from a reflection.

        Args:
            thread_id: Thread identifier
            index_in_thread: Question index when reflection was captured
            raw_reflection: User's freeform reflection
            thread_type: Type of thread
            project_profile: Optional project profile

        Returns:
            Created PlanNote
        """
        # Distill the reflection
        distilled, tags = self.distill_reflection(
            raw_reflection=raw_reflection,
            thread_type=thread_type,
            project_profile=project_profile
        )

        # Create the note
        note = PlanNote(
            id=str(uuid.uuid4()),
            thread_id=thread_id,
            index_in_thread=index_in_thread,
            raw=raw_reflection,
            distilled=distilled,
            tags=tags
        )

        logger.info(f"Created PlanNote {note.id} with {len(tags)} tags")
        return note

    def should_inject_reflection(
        self,
        thread: ThreadState,
        min_questions: int = 5,
        max_questions: int = 10
    ) -> bool:
        """
        Determine if a reflection should be injected.

        Args:
            thread: Thread state
            min_questions: Minimum questions before first reflection
            max_questions: Maximum questions before forcing reflection

        Returns:
            True if reflection should be injected
        """
        # Must have asked at least min_questions since last reflection
        if thread.questions_since_reflection < min_questions:
            return False

        # Force reflection if at max_questions
        if thread.questions_since_reflection >= max_questions:
            return True

        # Otherwise, probabilistic based on how close to max
        progress = (thread.questions_since_reflection - min_questions) / (max_questions - min_questions)
        import random
        return random.random() < progress * 0.5  # Up to 50% chance

    def extract_insights_from_notes(
        self,
        notes: List[PlanNote],
        focus_area: Optional[str] = None
    ) -> str:
        """
        Extract key insights from a collection of plan notes.

        Args:
            notes: List of plan notes
            focus_area: Optional focus area to filter insights

        Returns:
            Summary of key insights
        """
        if not notes:
            return "No reflections captured yet."

        # Group by tag prefix
        constraints = []
        risks = []
        preferences = []
        decisions = []
        insights = []

        for note in notes:
            for tag in note.tags:
                if tag.startswith("constraint:"):
                    constraints.append((note.distilled, tag))
                elif tag.startswith("risk:"):
                    risks.append((note.distilled, tag))
                elif tag.startswith("preference:"):
                    preferences.append((note.distilled, tag))
                elif tag.startswith("decision:"):
                    decisions.append((note.distilled, tag))
                elif tag.startswith("insight:"):
                    insights.append((note.distilled, tag))

        # Build summary
        summary_parts = []

        if constraints:
            summary_parts.append(f"**Constraints:** {len(constraints)} identified")
            for distilled, _ in constraints[:3]:
                summary_parts.append(f"  - {distilled}")

        if risks:
            summary_parts.append(f"**Risks:** {len(risks)} identified")
            for distilled, _ in risks[:3]:
                summary_parts.append(f"  - {distilled}")

        if decisions:
            summary_parts.append(f"**Key Decisions:** {len(decisions)}")
            for distilled, _ in decisions[:3]:
                summary_parts.append(f"  - {distilled}")

        if preferences:
            summary_parts.append(f"**Preferences:** {len(preferences)}")
            for distilled, _ in preferences[:2]:
                summary_parts.append(f"  - {distilled}")

        if insights:
            summary_parts.append(f"**Insights:** {len(insights)}")
            for distilled, _ in insights[:2]:
                summary_parts.append(f"  - {distilled}")

        return "\n".join(summary_parts)
