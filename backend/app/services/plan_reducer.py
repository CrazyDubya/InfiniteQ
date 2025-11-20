"""
Plan Reducer: maintains and updates the canonical plan state.
"""
import logging
from typing import List
from app.models.schema import PlanState, Answer, Question, CoverageMap, CoverageKey
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
        answers: List[Answer]
    ) -> PlanState:
        """
        Update plan state based on new answers.

        Args:
            plan_state: Current plan state
            questions: Questions that were asked
            answers: User's answers

        Returns:
            Updated plan state
        """
        try:
            # Build Q&A pairs
            qa_pairs = self._build_qa_pairs(questions, answers)
            if not qa_pairs:
                logger.warning("No valid Q&A pairs to process")
                return plan_state

            # Call model to update plan
            updated = self._call_reducer_model(plan_state, qa_pairs)
            if updated:
                logger.info("Plan state updated successfully")
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
        answers: List[Answer]
    ) -> CoverageMap:
        """
        Update coverage scores based on what was answered.

        Args:
            coverage: Current coverage
            questions: Questions that were asked
            answers: User's answers

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

        return CoverageMap(**updated)

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

    def _call_reducer_model(
        self,
        plan_state: PlanState,
        qa_pairs: List[dict]
    ) -> PlanState:
        """
        Call model to update plan state.

        Args:
            plan_state: Current plan
            qa_pairs: New Q&A pairs

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
                new_qa=qa_pairs
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
