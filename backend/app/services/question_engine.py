"""
Question Engine: generates next questions using multiple models.
Version 0.2: Adds support for profiles, threads, phases, and plan notes.
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.models.schema import (
    Question,
    CoverageMap,
    IdeaBrief,
    PlanState,
    QAPair,
    # v0.2 additions
    ProjectProfile,
    PersonaProfile,
    ThreadType,
    PlanNote,
    PhaseCoverageMap
)
from app.services.vultr_client import VultrClient
from app.services.model_registry import ModelRegistry
from app.prompts.templates import (
    QUESTION_GENERATION_SYSTEM,
    QUESTION_AGGREGATION_SYSTEM,
    format_question_generation_prompt,
    format_aggregation_prompt
)

logger = logging.getLogger(__name__)


class QuestionEngine:
    """
    Generates next questions by:
    1. Calling multiple models in parallel to propose questions
    2. Aggregating and deduplicating the proposals
    3. Selecting the best questions based on coverage
    """

    def __init__(self, vultr_client: VultrClient, model_registry: ModelRegistry):
        """
        Initialize question engine.

        Args:
            vultr_client: Vultr API client
            model_registry: Model registry for selecting models
        """
        self.client = vultr_client
        self.registry = model_registry
        self.max_workers = 4  # Parallel model calls

    def generate_questions(
        self,
        idea_brief: IdeaBrief,
        plan_state: PlanState,
        coverage: CoverageMap,
        recent_qa: List[QAPair],
        round_number: int = 0,
        # v0.2 additions
        project_profile: Optional[ProjectProfile] = None,
        persona_profile: Optional[PersonaProfile] = None,
        thread_type: Optional[ThreadType] = None,
        plan_notes: Optional[List[PlanNote]] = None,
        phase_coverage: Optional[PhaseCoverageMap] = None
    ) -> List[Question]:
        """
        Generate next questions using multi-model approach (v0.2: profile-aware).

        Args:
            idea_brief: Normalized idea
            plan_state: Current plan state
            coverage: Current coverage scores (thread-specific or global)
            recent_qa: Recent Q&A history
            round_number: Which round this is (affects model selection)
            project_profile: Project profile for contextualizing questions
            persona_profile: Persona profile for adjusting question style
            thread_type: Type of thread (for thread-specific questions)
            plan_notes: Recent reflections for context
            phase_coverage: Coverage by phase (for targeting weak phases)

        Returns:
            List of 2-4 questions to ask next
        """
        try:
            # Use defaults for backwards compatibility
            if project_profile is None:
                project_profile = ProjectProfile()
            if persona_profile is None:
                persona_profile = PersonaProfile()

            # Select models based on round number
            models = self._select_models_for_round(round_number)
            logger.info(f"Round {round_number}: Using models {models}")

            # Generate questions from each model in parallel
            candidates = self._generate_from_models(
                models=models,
                idea_brief=idea_brief,
                plan_state=plan_state,
                coverage=coverage,
                recent_qa=recent_qa,
                project_profile=project_profile,
                persona_profile=persona_profile,
                thread_type=thread_type,
                plan_notes=plan_notes or [],
                phase_coverage=phase_coverage
            )

            if not candidates:
                logger.warning("No candidates generated, using fallback")
                return self._fallback_questions(coverage)

            # Aggregate and select best questions
            final_questions = self._aggregate_questions(candidates, coverage)

            logger.info(f"Generated {len(final_questions)} questions")
            return final_questions

        except Exception as e:
            logger.error(f"Question generation failed: {e}", exc_info=True)
            return self._fallback_questions(coverage)

    def _select_models_for_round(self, round_number: int) -> List[str]:
        """
        Select which models to use based on the round number.

        Early rounds: strategy + reasoning
        Mid rounds: add tech models
        Later rounds: more diverse mix

        Args:
            round_number: Current round

        Returns:
            List of model IDs to use
        """
        if round_number < 2:
            # Early: strategy and reasoning
            return (
                self.registry.pick_strategy_models(k=2) +
                self.registry.pick_reasoning_models(k=1)
            )
        elif round_number < 5:
            # Mid: add tech models
            return (
                self.registry.pick_strategy_models(k=1) +
                self.registry.pick_reasoning_models(k=1) +
                self.registry.pick_tech_models(k=1)
            )
        else:
            # Later: diverse mix
            return (
                self.registry.pick_strategy_models(k=1) +
                self.registry.pick_tech_models(k=1) +
                self.registry.pick_reasoning_models(k=1)
            )

    def _generate_from_models(
        self,
        models: List[str],
        idea_brief: IdeaBrief,
        plan_state: PlanState,
        coverage: CoverageMap,
        recent_qa: List[QAPair],
        project_profile: ProjectProfile,
        persona_profile: PersonaProfile,
        thread_type: Optional[ThreadType],
        plan_notes: List[PlanNote],
        phase_coverage: Optional[PhaseCoverageMap]
    ) -> List[Dict[str, Any]]:
        """
        Call multiple models in parallel to generate question candidates (v0.2: profile-aware).

        Args:
            models: List of model IDs
            idea_brief: Idea brief
            plan_state: Plan state
            coverage: Coverage map
            recent_qa: Recent Q&A
            project_profile: Project profile
            persona_profile: Persona profile
            thread_type: Thread type
            plan_notes: Plan notes from reflections
            phase_coverage: Coverage by phase

        Returns:
            List of candidate sets from each model
        """
        # Prepare v0.2 prompt with profiles
        user_prompt = format_question_generation_prompt(
            idea_brief=idea_brief.model_dump(),
            plan_state=plan_state.model_dump(),
            coverage=coverage.model_dump(),
            recent_qa=[{
                "q": qa.question.text,
                "a": f"{qa.answer.choice_id}: {qa.answer.free_text or ''}"
            } for qa in recent_qa],
            max_questions=3,
            # v0.2 additions
            project_profile=project_profile.model_dump(),
            persona_profile=persona_profile.model_dump(),
            thread_type=thread_type.value if thread_type else None,
            plan_notes=[{
                "distilled": note.distilled,
                "tags": note.tags
            } for note in plan_notes[-5:]],  # Last 5 notes
            phase_coverage=phase_coverage.model_dump() if phase_coverage else None
        )

        messages = [
            {"role": "system", "content": QUESTION_GENERATION_SYSTEM},
            {"role": "user", "content": user_prompt}
        ]

        # Call models in parallel
        candidates = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_model = {
                executor.submit(
                    self._call_model_for_questions,
                    model,
                    messages
                ): model
                for model in models
            }

            for future in as_completed(future_to_model):
                model = future_to_model[future]
                try:
                    result = future.result()
                    if result:
                        candidates.append({
                            "model": model,
                            "questions": result
                        })
                except Exception as e:
                    logger.error(f"Model {model} failed: {e}")

        return candidates

    def _call_model_for_questions(
        self,
        model: str,
        messages: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Call a single model to generate questions.

        Args:
            model: Model ID
            messages: Prompt messages

        Returns:
            List of question dicts
        """
        try:
            result = self.client.chat_completion_json(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )

            if isinstance(result, dict) and "questions" in result:
                return result["questions"]
            return []

        except Exception as e:
            logger.error(f"Model {model} call failed: {e}")
            return []

    def _aggregate_questions(
        self,
        candidates: List[Dict[str, Any]],
        coverage: CoverageMap
    ) -> List[Question]:
        """
        Aggregate questions from multiple models into final set.

        Args:
            candidates: Candidate question sets
            coverage: Current coverage

        Returns:
            Final selected questions
        """
        if not candidates:
            return []

        # If only one candidate set, use it directly
        if len(candidates) == 1:
            return self._parse_questions(candidates[0]["questions"])

        # Use aggregation model
        try:
            aggregator_model = self.registry.pick_reasoning_models(k=1)[0]
            user_prompt = format_aggregation_prompt(
                coverage=coverage.model_dump(),
                candidates=candidates
            )

            messages = [
                {"role": "system", "content": QUESTION_AGGREGATION_SYSTEM},
                {"role": "user", "content": user_prompt}
            ]

            result = self.client.chat_completion_json(
                model=aggregator_model,
                messages=messages,
                temperature=0.3,
                max_tokens=2000
            )

            if isinstance(result, dict) and "questions" in result:
                return self._parse_questions(result["questions"])

        except Exception as e:
            logger.error(f"Aggregation failed: {e}")

        # Fallback: take top questions from first candidate
        return self._parse_questions(candidates[0]["questions"][:3])

    def _parse_questions(self, questions_data: List[Dict[str, Any]]) -> List[Question]:
        """
        Parse question dicts into Question models.

        Args:
            questions_data: Raw question data

        Returns:
            List of Question objects
        """
        parsed = []
        for q_data in questions_data:
            try:
                question = Question(**q_data)
                parsed.append(question)
            except Exception as e:
                logger.error(f"Failed to parse question: {e}")

        return parsed

    def _fallback_questions(self, coverage: CoverageMap) -> List[Question]:
        """
        Generate fallback questions when generation fails.

        Args:
            coverage: Current coverage

        Returns:
            Basic fallback questions
        """
        from app.models.schema import QuestionOption, CoverageKey

        # Find lowest coverage area
        coverage_dict = coverage.model_dump()
        lowest_key = min(coverage_dict.keys(), key=lambda k: coverage_dict[k])

        return [
            Question(
                id="FALLBACK_001",
                coverage_key=CoverageKey(lowest_key),
                priority=0.9,
                text=f"What's most important to clarify about the {lowest_key}?",
                options=[
                    QuestionOption(id="A", text="Provide more details", effect="expand"),
                    QuestionOption(id="B", text="Keep it simple for now", effect="defer"),
                    QuestionOption(id="OTHER", text="Other (please specify)", effect="custom")
                ]
            )
        ]
