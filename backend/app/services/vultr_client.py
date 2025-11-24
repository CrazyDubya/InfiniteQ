"""
Vultr Serverless Inference client.
Wraps the OpenAI-compatible API at https://api.vultrinference.com/v1
"""
import os
import json
import copy
import logging
from typing import List, Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class VultrClient:
    """Client for Vultr Serverless Inference API."""

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.vultrinference.com/v1"):
        """
        Initialize Vultr client.

        Args:
            api_key: Vultr API key (defaults to VULTR_INFERENCE_API_KEY env var)
            base_url: Base URL for the API
        """
        self.api_key = api_key or os.environ.get("VULTR_INFERENCE_API_KEY")
        if not self.api_key:
            raise ValueError("VULTR_INFERENCE_API_KEY environment variable or api_key parameter required")

        self.base_url = base_url
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _headers(self) -> Dict[str, str]:
        """Get request headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def list_models(self) -> List[Dict[str, Any]]:
        """
        List available chat models.

        Returns:
            List of model info dictionaries
        """
        url = f"{self.base_url}/chat/models"
        try:
            response = self.session.get(url, headers=self._headers(), timeout=10)
            response.raise_for_status()
            data = response.json()

            # The API returns {"data": [{"id": "...", ...}, ...]}
            if isinstance(data, dict) and "data" in data:
                return data["data"]
            return data if isinstance(data, list) else []

        except requests.RequestException as e:
            logger.error(f"Failed to list models: {e}")
            raise

    def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Call chat completion endpoint.

        Args:
            model: Model ID to use
            messages: List of message dicts with "role" and "content"
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            Generated text content
        """
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            **kwargs
        }

        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        try:
            response = self.session.post(
                url,
                headers=self._headers(),
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()

            # Extract content from response
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]

            raise ValueError(f"Unexpected response format: {data}")

        except requests.RequestException as e:
            logger.error(f"Chat completion failed for model {model}: {e}")
            raise
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"Failed to parse response: {e}")
            raise

    def chat_completion_json(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call chat completion and parse response as JSON.

        Args:
            model: Model ID to use
            messages: List of message dicts
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            Parsed JSON object
        """
        # Deep copy messages to avoid mutating the caller's list
        messages = copy.deepcopy(messages)

        # Add JSON format instruction to system message if not present
        if messages and messages[0]["role"] == "system":
            if "JSON" not in messages[0]["content"]:
                messages[0]["content"] += "\n\nYou must respond with valid JSON only, no additional text."

        content = self.chat_completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

        # Try to extract JSON if wrapped in markdown code blocks
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}\nContent: {content[:500]}")
            raise ValueError(f"Model {model} did not return valid JSON: {e}")
