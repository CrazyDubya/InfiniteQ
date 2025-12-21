"""
Coverage Quality Assessor: Uses LLM to semantically assess answer quality.
Replaces the simplistic length-based coverage calculation.
"""
import logging
from typing import List, Dict, Optional, Tuple
from app.models.schema import (
    Question,
    Answer,
    CoverageMap,
    CoverageKey,
    PlanState
)
from app.services.vultr_client import VultrClient
from app.services.model_registry import ModelRegistry

logger = logging.getLogger(__name__)


COVERAGE_ASSESSMENT_PROMPT = """You are evaluating the quality and completeness of answers in a project planning interview.

Question asked:
"{question_text}"

Coverage dimension: {coverage_key}

User's answer:
- Selected option: {choice_text}
- Additional context: {free_text}

Current plan state for this dimension:
{plan_context}

Rate the answer quality on these criteria:

1. **Specificity** (0-25): How specific and actionable is the answer?
   - 0-5: Vague or generic ("something good")
   - 6-15: Somewhat specific ("a web app for users")
   - 16-25: Very specific ("React SPA with OAuth2 login for NYC landlords")

2. **Completeness** (0-25): Does it fully address the question?
   - 0-5: Barely addresses the question
   - 6-15: Partially addresses the question
   - 16-25: Fully addresses with additional context

3. **Novelty** (0-25): Does it add new information to the plan?
   - 0-5: Repeats existing information
   - 6-15: Adds some new details
   - 16-25: Significant new information or decisions

4. **Clarity** (0-25): Is the answer clear and unambiguous?
   - 0-5: Confusing or contradictory
   - 6-15: Understandable but could be clearer
   - 16-25: Crystal clear, no ambiguity

Output as JSON:
{{
    "specificity": 0-25,
    "completeness": 0-25,
    "novelty": 0-25,
    "clarity": 0-25,
    "total_score": 0-100,
    "confidence": 0.0-1.0,
    "key_insights": ["insight1", "insight2"],
    "gaps_identified": ["gap1", "gap2"],
    "reasoning": "Brief explanation"
}}

Output ONLY valid JSON."""


DIMENSION_COMPLETENESS_PROMPT = """Assess how complete the planning is for this dimension.

Dimension: {dimension}

Current plan content:
{plan_content}

All Q&A history for this dimension:
{qa_history}

Rate completeness on a scale of 0-100:
- 0-20: Almost nothing defined
- 21-40: Basic outline only
- 41-60: Key aspects covered but gaps remain
- 61-80: Well-defined with minor gaps
- 81-100: Comprehensive and thorough

Output as JSON:
{{
    "completeness_score": 0-100,
    "covered_aspects": ["aspect1", "aspect2"],
    "missing_aspects": ["missing1", "missing2"],
    "recommended_questions": ["question1", "question2"],
    "confidence": 0.0-1.0
}}

Output ONLY valid JSON."""


class CoverageQualityAssessor:
    """
    Semantically assesses answer quality and coverage completeness.
    Provides intelligent coverage scoring instead of simple length-based.
    """

    def __init__(self, vultr_client: VultrClient, model_registry: ModelRegistry):
        """
        Initialize assessor.

        Args:
            vultr_client: Vultr API client
            model_registry: Model registry for selecting models
        """
        self.client = vultr_client
        self.registry = model_registry

    def assess_answer(
        self,
        question: Question,
        answer: Answer,
        plan_state: PlanState
    ) -> Tuple[float, Dict]:
        """
        Assess the quality of an answer and return coverage increment.

        Args:
            question: The question asked
            answer: User's answer
            plan_state: Current plan state

        Returns:
            Tuple of (coverage_increment, assessment_details)
        """
        try:
            model = self._get_model()

            # Get plan context for this dimension
            plan_context = self._get_plan_context(question.coverage_key, plan_state)

            # Find the choice text
            choice_text = answer.choice_id
            for opt in question.options:
                if opt.id == answer.choice_id:
                    choice_text = opt.text
                    break

            prompt = COVERAGE_ASSESSMENT_PROMPT.format(
                question_text=question.text,
                coverage_key=question.coverage_key.value,
                choice_text=choice_text,
                free_text=answer.free_text or "(none provided)",
                plan_context=plan_context
            )

            result = self.client.chat_completion_json(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1000
            )

            if isinstance(result, dict):
                total_score = result.get("total_score", 50)
                confidence = result.get("confidence", 0.7)

                # Convert 0-100 score to coverage increment (max 25 per answer)
                # Higher quality answers contribute more to coverage
                increment = (total_score / 100.0) * 25.0 * confidence

                return increment, {
                    "score": total_score,
                    "confidence": confidence,
                    "specificity": result.get("specificity", 0),
                    "completeness": result.get("completeness", 0),
                    "novelty": result.get("novelty", 0),
                    "clarity": result.get("clarity", 0),
                    "insights": result.get("key_insights", []),
                    "gaps": result.get("gaps_identified", []),
                    "reasoning": result.get("reasoning", "")
                }

        except Exception as e:
            logger.error(f"Answer assessment failed: {e}")

        # Fallback to heuristic scoring
        return self._heuristic_score(answer), {"score": 50, "confidence": 0.3, "reasoning": "Heuristic fallback"}

    def assess_dimension_completeness(
        self,
        dimension: CoverageKey,
        plan_state: PlanState,
        qa_history: List[Dict]
    ) -> Tuple[float, Dict]:
        """
        Assess overall completeness of a coverage dimension.

        Args:
            dimension: The coverage dimension to assess
            plan_state: Current plan state
            qa_history: Q&A history for this dimension

        Returns:
            Tuple of (completeness_score, assessment_details)
        """
        try:
            model = self._get_model()

            plan_content = self._get_plan_context(dimension, plan_state)

            # Format QA history
            qa_formatted = "\n".join([
                f"Q: {qa.get('question', 'Unknown')}\nA: {qa.get('answer', 'Unknown')}"
                for qa in qa_history[-10:]  # Last 10 for context
            ])

            prompt = DIMENSION_COMPLETENESS_PROMPT.format(
                dimension=dimension.value,
                plan_content=plan_content,
                qa_history=qa_formatted or "(no history)"
            )

            result = self.client.chat_completion_json(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1000
            )

            if isinstance(result, dict):
                return result.get("completeness_score", 0), {
                    "covered": result.get("covered_aspects", []),
                    "missing": result.get("missing_aspects", []),
                    "recommended_questions": result.get("recommended_questions", []),
                    "confidence": result.get("confidence", 0.5)
                }

        except Exception as e:
            logger.error(f"Dimension assessment failed: {e}")

        return 0.0, {"confidence": 0.0}

    def recalculate_coverage(
        self,
        plan_state: PlanState,
        qa_history: Dict[str, List[Dict]]
    ) -> CoverageMap:
        """
        Recalculate all coverage scores using semantic assessment.

        Args:
            plan_state: Current plan state
            qa_history: Q&A history grouped by dimension

        Returns:
            Recalculated coverage map
        """
        coverage_dict = {}

        for dimension in CoverageKey:
            history = qa_history.get(dimension.value, [])
            score, _ = self.assess_dimension_completeness(
                dimension, plan_state, history
            )
            coverage_dict[dimension.value] = min(100.0, max(0.0, score))

        return CoverageMap(**coverage_dict)

    def _get_model(self) -> str:
        """Get a reasoning model for assessment."""
        models = self.registry.pick_reasoning_models(k=1)
        return models[0] if models else "llama-3.3-70b-instruct-fp8"

    def _get_plan_context(self, dimension: CoverageKey, plan_state: PlanState) -> str:
        """Extract plan content relevant to a dimension."""
        contexts = {
            CoverageKey.PROBLEM: f"Summary: {plan_state.problem.summary}\nPain points: {plan_state.problem.pain_points}",
            CoverageKey.USERS: str([{"role": u.role, "needs": u.needs} for u in plan_state.users]),
            CoverageKey.CONSTRAINTS: f"Time: {plan_state.constraints.time}, Budget: {plan_state.constraints.budget}, Technical: {plan_state.constraints.technical}",
            CoverageKey.FEATURES: str([{"title": f.title, "must_have": f.must_have} for f in plan_state.features]),
            CoverageKey.ARCHITECTURE: f"Frontend: {plan_state.architecture.frontend}, Backend: {plan_state.architecture.backend}, Data: {plan_state.architecture.data}",
            CoverageKey.DATA_ML: f"Data: {plan_state.architecture.data}",
            CoverageKey.OPERATIONS: f"Infrastructure: {plan_state.architecture.infrastructure}",
            CoverageKey.RISKS: str([{"risk": r.risk, "mitigation": r.mitigation} for r in plan_state.risks]),
            CoverageKey.GTM: f"Type: {plan_state.meta.type}, Users: {len(plan_state.users)} personas defined"
        }
        return contexts.get(dimension, "(no content)")

    def _heuristic_score(self, answer: Answer) -> float:
        """Fallback heuristic scoring when LLM fails."""
        base_score = 10.0

        # Bonus for free text
        if answer.free_text:
            text_len = len(answer.free_text)
            if text_len > 100:
                base_score += 15.0
            elif text_len > 50:
                base_score += 10.0
            elif text_len > 20:
                base_score += 5.0

        return base_score


class SmartReflectionTrigger:
    """
    Intelligent reflection trigger based on conversation patterns.
    Replaces the random 5-10 question trigger.
    """

    def __init__(self, vultr_client: VultrClient = None, model_registry: ModelRegistry = None):
        self.client = vultr_client
        self.registry = model_registry

    def should_trigger_reflection(
        self,
        questions_since_last: int,
        recent_answers: List[Answer],
        coverage_map: CoverageMap,
        previous_coverage: Optional[CoverageMap] = None
    ) -> Tuple[bool, str]:
        """
        Determine if a reflection should be triggered.

        Returns:
            Tuple of (should_trigger, reason)
        """
        # Minimum threshold
        if questions_since_last < 3:
            return False, "Too early"

        # Maximum threshold (always trigger after 12)
        if questions_since_last >= 12:
            return True, "Maximum interval reached"

        # Trigger on coverage plateau
        if previous_coverage:
            current_total = sum(coverage_map.model_dump().values())
            previous_total = sum(previous_coverage.model_dump().values())
            if current_total - previous_total < 5.0 and questions_since_last >= 5:
                return True, "Coverage plateau detected"

        # Trigger on short answers (possible confusion)
        short_answers = sum(
            1 for a in recent_answers[-3:]
            if not a.free_text or len(a.free_text) < 10
        )
        if short_answers >= 2 and questions_since_last >= 5:
            return True, "Short answers suggest need for reflection"

        # Trigger on major dimension coverage gap
        coverage_dict = coverage_map.model_dump()
        max_coverage = max(coverage_dict.values())
        min_coverage = min(coverage_dict.values())
        if max_coverage - min_coverage > 40 and questions_since_last >= 6:
            return True, "Large coverage imbalance"

        return False, "No trigger condition met"

    def generate_reflection_prompt(
        self,
        trigger_reason: str,
        coverage_map: CoverageMap,
        thread_type: str
    ) -> str:
        """Generate a contextual reflection prompt."""
        coverage_dict = coverage_map.model_dump()
        lowest_dim = min(coverage_dict.keys(), key=lambda k: coverage_dict[k])

        prompts = {
            "Coverage plateau detected": f"We've covered a lot of ground. What important details about {lowest_dim} might we be missing?",
            "Short answers suggest need for reflection": "I sense there might be some complexity we're not capturing. What's the trickiest part of this project that's hard to put into words?",
            "Large coverage imbalance": f"We've explored some areas deeply but {lowest_dim} needs more attention. What should I know about {lowest_dim}?",
            "Maximum interval reached": f"Let's pause and reflect. In the context of {thread_type}, what constraints, risks, or preferences haven't we discussed yet?"
        }

        return prompts.get(
            trigger_reason,
            f"What's the most important thing about this {thread_type} thread that we haven't captured yet?"
        )
