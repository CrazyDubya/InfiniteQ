"""
Model Registry: discovers, categorizes, and selects Vultr models.
"""
import logging
import re
from typing import List, Optional, Dict
from app.models.schema import ModelInfo, ModelRole
from app.services.vultr_client import VultrClient

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Discovers and manages available Vultr models.
    Categorizes models by role and provides selection logic.
    """

    # Model classification rules based on name patterns
    MODEL_PATTERNS = {
        ModelRole.REASONING: [
            "deepseek-r1",
            "deepseek-reasoner",
            "qwen.*think",
        ],
        ModelRole.CODE_TECH: [
            "coder",
            "codestral",
            "qwen.*coder",
            "deepseek.*coder",
        ],
        ModelRole.SYNTHESIS: [
            "llama-3.3-70b",
            "llama-3.1-70b",
            "kimi-k2",
            "qwen2.5-72b",
        ],
        ModelRole.STRATEGY: [
            "kimi",
            "claude",
            "gpt-4",
            "llama.*instruct",
        ],
    }

    def __init__(self, vultr_client: VultrClient):
        """
        Initialize registry.

        Args:
            vultr_client: Vultr API client
        """
        self.client = vultr_client
        self.models: List[ModelInfo] = []
        # Set when discovery fails and the hardcoded fallbacks are used, so a
        # bad API key surfaces in /health instead of looking healthy.
        self.discovery_error: Optional[str] = None
        self._models_by_role: Dict[ModelRole, List[ModelInfo]] = {
            role: [] for role in ModelRole
        }

    def discover_models(self) -> List[ModelInfo]:
        """
        Discover available models from Vultr API and categorize them.

        Returns:
            List of categorized models
        """
        try:
            raw_models = self.client.list_models()
            logger.info(f"Discovered {len(raw_models)} models from Vultr")

            self.models = []
            for model_data in raw_models:
                model_id = model_data.get("id", "")
                if not model_id:
                    continue

                # Categorize by role
                role = self._categorize_model(model_id)
                priority = self._assign_priority(model_id, role)

                model_info = ModelInfo(
                    id=model_id,
                    role=role,
                    priority=priority
                )
                self.models.append(model_info)

            # Group by role
            self._models_by_role = {role: [] for role in ModelRole}
            for model in self.models:
                self._models_by_role[model.role].append(model)

            # Sort by priority within each role
            for role in ModelRole:
                self._models_by_role[role].sort(key=lambda m: m.priority, reverse=True)

            self.discovery_error = None
            logger.info(f"Categorized models: {self._get_role_counts()}")
            return self.models

        except Exception as e:
            self.discovery_error = str(e)
            logger.error(f"Failed to discover models: {e}")
            # Fall back to hardcoded models
            return self._fallback_models()

    def _categorize_model(self, model_id: str) -> ModelRole:
        """
        Categorize a model by its ID.

        Patterns are regular expressions (some of them, like "qwen.*think",
        only make sense as such), matched most-specific-role first.

        Args:
            model_id: Model identifier

        Returns:
            Assigned role
        """
        model_lower = model_id.lower()

        for role in (
            ModelRole.REASONING,   # most specific
            ModelRole.CODE_TECH,
            ModelRole.SYNTHESIS,
            ModelRole.STRATEGY,
        ):
            for pattern in self.MODEL_PATTERNS[role]:
                if re.search(pattern, model_lower):
                    return role

        # Default to general
        return ModelRole.GENERAL

    def _assign_priority(self, model_id: str, role: ModelRole) -> int:
        """
        Assign priority to a model within its role.

        Args:
            model_id: Model identifier
            role: Assigned role

        Returns:
            Priority score (higher = better)
        """
        priority = 1
        model_lower = model_id.lower()

        # Size-based priority
        if "70b" in model_lower or "72b" in model_lower:
            priority += 3
        elif "32b" in model_lower:
            priority += 2
        elif "7b" in model_lower or "8b" in model_lower:
            priority += 1

        # Model family bonuses
        if "llama-3.3" in model_lower:
            priority += 2
        elif "qwen2.5" in model_lower:
            priority += 2
        elif "deepseek" in model_lower:
            priority += 1

        # Instruction-tuned models preferred
        if "instruct" in model_lower:
            priority += 1

        return priority

    def _get_role_counts(self) -> Dict[str, int]:
        """Get count of models per role."""
        return {
            role.value: len(models)
            for role, models in self._models_by_role.items()
        }

    def pick_reasoning_models(self, k: int = 2) -> List[str]:
        """
        Pick top k reasoning models.

        Args:
            k: Number of models to select

        Returns:
            List of model IDs
        """
        return self._pick_models_by_role(ModelRole.REASONING, k)

    def pick_tech_models(self, k: int = 2) -> List[str]:
        """
        Pick top k code/tech models.

        Args:
            k: Number of models to select

        Returns:
            List of model IDs
        """
        return self._pick_models_by_role(ModelRole.CODE_TECH, k)

    def pick_synthesis_model(self) -> Optional[str]:
        """
        Pick the best synthesis model.

        Returns:
            Model ID or None
        """
        models = self._pick_models_by_role(ModelRole.SYNTHESIS, 1)
        return models[0] if models else None

    def pick_strategy_models(self, k: int = 2) -> List[str]:
        """
        Pick top k strategy models.

        Args:
            k: Number of models to select

        Returns:
            List of model IDs
        """
        return self._pick_models_by_role(ModelRole.STRATEGY, k)

    def _pick_models_by_role(self, role: ModelRole, k: int) -> List[str]:
        """
        Pick top k models for a role.

        Args:
            role: Model role
            k: Number to select

        Returns:
            List of model IDs
        """
        models = self._models_by_role.get(role, [])
        selected = models[:k]

        # If not enough models in primary role, fall back to GENERAL
        if len(selected) < k and role != ModelRole.GENERAL:
            general = self._models_by_role.get(ModelRole.GENERAL, [])
            needed = k - len(selected)
            selected.extend(general[:needed])

        return [m.id for m in selected]

    def _fallback_models(self) -> List[ModelInfo]:
        """
        Provide hardcoded fallback models if discovery fails.

        Returns:
            List of fallback models
        """
        fallback = [
            ModelInfo(id="llama-3.3-70b-instruct-fp8", role=ModelRole.SYNTHESIS, priority=5),
            ModelInfo(id="qwen2.5-coder-32b-instruct", role=ModelRole.CODE_TECH, priority=4),
            ModelInfo(id="deepseek-r1-distill-qwen-32b", role=ModelRole.REASONING, priority=4),
            ModelInfo(id="llama-3.1-70b-instruct", role=ModelRole.STRATEGY, priority=3),
        ]

        self.models = fallback
        self._models_by_role = {role: [] for role in ModelRole}
        for model in fallback:
            self._models_by_role[model.role].append(model)

        logger.warning("Using fallback models")
        return fallback

    def get_all_models(self) -> List[ModelInfo]:
        """Get all registered models."""
        return self.models

    def get_models_by_role(self, role: ModelRole) -> List[ModelInfo]:
        """Get all models for a specific role."""
        return self._models_by_role.get(role, [])
