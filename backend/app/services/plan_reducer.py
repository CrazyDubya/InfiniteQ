"""
Plan Reducer: maintains and updates the canonical plan state.
Version 0.2: Adds thread-aware updates, plan notes processing, and phase coverage.
"""
import logging
from typing import List, Optional
from app.models.schema import (
    PlanState,
    Answer,
    Question,
    CoverageMap,
    CoverageKey,
    # v0.2 additions
    PlanNote,
    PhaseCoverageMap,
    Phase,
    ProjectProfile
)
from app.services.vultr_client import VultrClient
from app.services.model_registry import ModelRegistry
from app.prompts.templates import (
    PLAN_REDUCER_SYSTEM,
    format_plan_reducer_prompt
)

logger = logging.getLogger(__name__)


class PlanReducer:
    """
    Maintains the canonical plan state.
    After each answer round, updates the plan intelligently.
    """

    def __init__(self, vultr_client: VultrClient, model_registry: ModelRegistry):
        """
        Initialize plan reducer.

        Args:
            vultr_client: Vultr API client
            model_registry: Model registry for selecting models
        """
        self.client = vultr_client
        self.registry = model_registry

    def update_plan(
        self,
        plan_state: PlanState,
        questions: List[Question],
        answers: List[Answer],
        # v0.2 additions
        thread_id: Optional[str] = None,
        plan_notes: Optional[List[PlanNote]] = None,
        project_profile: Optional[ProjectProfile] = None
    ) -> PlanState:
        """
        Update plan state based on new answers (v0.2: with thread and notes context).

        Args:
            plan_state: Current plan state
            questions: Questions that were asked
            answers: User's answers
            thread_id: Thread identifier (for thread-aware updates)
            plan_notes: Plan notes from reflections
            project_profile: Project profile for context

        Returns:
            Updated plan state
        """
        try:
            # Build Q&A pairs
            qa_pairs = self._build_qa_pairs(questions, answers)
            if not qa_pairs:
                logger.warning("No valid Q&A pairs to process")
                return plan_state

            # v0.2: Build context from plan notes
            notes_context = self._extract_notes_context(plan_notes) if plan_notes else {}

            # Call model to update plan
            updated = self._call_reducer_model(
                plan_state=plan_state,
                qa_pairs=qa_pairs,
                thread_id=thread_id,
                notes_context=notes_context,
                project_profile=project_profile
            )
            if updated:
                logger.info(f"Plan state updated successfully (thread: {thread_id or 'global'})")
                return updated

            logger.warning("Model update failed, returning original state")
            return plan_state

        except Exception as e:
            logger.error(f"Plan update failed: {e}", exc_info=True)
            return plan_state

    def update_coverage(
        self,
        coverage: CoverageMap,
        questions: List[Question],
        answers: List[Answer],
        # v0.2: Optional phase coverage tracking
        phase_coverage: Optional[PhaseCoverageMap] = None
    ) -> CoverageMap:
        """
        Update coverage scores based on what was answered (v0.2: with phase support).

        Args:
            coverage: Current coverage
            questions: Questions that were asked
            answers: User's answers
            phase_coverage: Phase-specific coverage (will be updated in-place if provided)

        Returns:
            Updated coverage
        """
        # Map questions to their coverage keys
        question_map = {q.id: q for q in questions}

        updated = coverage.model_dump()

        for answer in answers:
            question = question_map.get(answer.question_id)
            if not question:
                continue

            # Increase coverage for this dimension
            key = question.coverage_key.value
            if key in updated:
                # Add points based on answer specificity
                increment = 15.0  # Base increment

                # More detail = more coverage
                if answer.free_text and len(answer.free_text) > 20:
                    increment += 10.0

                # Don't exceed 100
                updated[key] = min(100.0, updated[key] + increment)

                # v0.2: Update phase coverage if question has phase
                if phase_coverage and question.phase:
                    self._update_phase_coverage(
                        phase_coverage=phase_coverage,
                        phase=question.phase,
                        coverage_key=key,
                        increment=increment
                    )

        return CoverageMap(**updated)

    def _update_phase_coverage(
        self,
        phase_coverage: PhaseCoverageMap,
        phase: Phase,
        coverage_key: str,
        increment: float
    ):
        """
        Update phase-specific coverage (in-place).

        Args:
            phase_coverage: Phase coverage map
            phase: Target phase
            coverage_key: Coverage dimension key
            increment: Points to add
        """
        phase_map = {
            Phase.PROTOTYPE: phase_coverage.prototype,
            Phase.V1: phase_coverage.v1,
            Phase.SCALE_UP: phase_coverage.scale_up,
            Phase.V2_PLUS: phase_coverage.v2_plus
        }

        if phase in phase_map:
            coverage_obj = phase_map[phase]
            current_value = getattr(coverage_obj, coverage_key, 0.0)
            setattr(coverage_obj, coverage_key, min(100.0, current_value + increment))

    def _build_qa_pairs(
        self,
        questions: List[Question],
        answers: List[Answer]
    ) -> List[dict]:
        """
        Build Q&A pairs for the model.

        Args:
            questions: Questions asked
            answers: Answers provided

        Returns:
            List of Q&A pair dicts
        """
        question_map = {q.id: q for q in questions}
        pairs = []

        for answer in answers:
            question = question_map.get(answer.question_id)
            if not question:
                continue

            # Find the selected option
            option = next(
                (opt for opt in question.options if opt.id == answer.choice_id),
                None
            )

            pairs.append({
                "question_id": question.id,
                "question_text": question.text,
                "coverage_key": question.coverage_key.value,
                "choice": answer.choice_id,
                "choice_text": option.text if option else answer.choice_id,
                "choice_effect": option.effect if option else "unknown",
                "free_text": answer.free_text
            })

        return pairs

    def _extract_notes_context(self, plan_notes: List[PlanNote]) -> dict:
        """
        Extract context from plan notes for reducer (v0.2).

        Args:
            plan_notes: List of plan notes

        Returns:
            Dict with organized note context
        """
        context = {
            "constraints": [],
            "risks": [],
            "preferences": [],
            "decisions": [],
            "insights": []
        }

        for note in plan_notes:
            for tag in note.tags:
                if tag.startswith("constraint:"):
                    context["constraints"].append({
                        "tag": tag,
                        "note": note.distilled
                    })
                elif tag.startswith("risk:"):
                    context["risks"].append({
                        "tag": tag,
                        "note": note.distilled
                    })
                elif tag.startswith("preference:"):
                    context["preferences"].append({
                        "tag": tag,
                        "note": note.distilled
                    })
                elif tag.startswith("decision:"):
                    context["decisions"].append({
                        "tag": tag,
                        "note": note.distilled
                    })
                elif tag.startswith("insight:"):
                    context["insights"].append({
                        "tag": tag,
                        "note": note.distilled
                    })

        return context

    def _call_reducer_model(
        self,
        plan_state: PlanState,
        qa_pairs: List[dict],
        thread_id: Optional[str] = None,
        notes_context: Optional[dict] = None,
        project_profile: Optional[ProjectProfile] = None
    ) -> PlanState:
        """
        Call model to update plan state (v0.2: with thread and notes context).

        Args:
            plan_state: Current plan
            qa_pairs: New Q&A pairs
            thread_id: Thread identifier
            notes_context: Context from plan notes
            project_profile: Project profile

        Returns:
            Updated plan state
        """
        try:
            # Use a reasoning model for plan updates
            models = self.registry.pick_reasoning_models(k=1)
            if not models:
                raise ValueError("No reasoning models available")

            model = models[0]

            user_prompt = format_plan_reducer_prompt(
                plan_state=plan_state.model_dump(),
                new_qa=qa_pairs,
                # v0.2 additions
                thread_id=thread_id,
                notes_context=notes_context,
                project_profile=project_profile.model_dump() if project_profile else None
            )

            messages = [
                {"role": "system", "content": PLAN_REDUCER_SYSTEM},
                {"role": "user", "content": user_prompt}
            ]

            result = self.client.chat_completion_json(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=3000
            )

            # Parse result into PlanState
            return PlanState(**result)

        except Exception as e:
            logger.error(f"Reducer model call failed: {e}")
            raise

    def initialize_plan(self, idea_brief: dict) -> PlanState:
        """
        Initialize a plan from an idea brief.

        Args:
            idea_brief: Normalized idea

        Returns:
            Initial plan state
        """
        plan = PlanState()

        # Set basic metadata from idea
        plan.meta.title = idea_brief.get("normalized_summary", "")[:100]
        plan.meta.type = idea_brief.get("inferred_type", "software")

        # Set problem summary
        plan.problem.summary = idea_brief.get("normalized_summary", "")

        return plan
