"""LLM Client for interacting with OpenAI or Ollama.

Referencing implementation plan:
- Supports OpenAI (gpt-4o-mini) and Ollama (llama3.2).
- Returns structured JSON for scoring.
"""

import json
import logging
from typing import Any

from openai import OpenAI
import httpx

from src.config import get_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for LLM interactions."""

    def __init__(self):
        self.settings = get_settings()
        self.provider = self.settings.llm_provider
        
        if self.provider == "openai":
            self.client = OpenAI(api_key=self.settings.openai_api_key)
        else:
            # Ollama doesn't need a client instance, we'll use httpx directly
            pass

    def get_completion(self, prompt: str, system_prompt: str = "You are a helpful AI assistant.") -> str:
        """Get completion from configured LLM provider."""
        if self.provider == "openai":
            return self._get_openai_completion(prompt, system_prompt)
        elif self.provider == "ollama":
            return self._get_ollama_completion(prompt, system_prompt)
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")

    def _get_openai_completion(self, prompt: str, system_prompt: str) -> str:
        """Call OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return ""

    def _get_ollama_completion(self, prompt: str, system_prompt: str) -> str:
        """Call Ollama API."""
        url = f"{self.settings.ollama_base_url}/api/chat"
        payload = {
            "model": self.settings.ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "format": "json", # Ollama supports JSON mode
        }
        
        try:
            response = httpx.post(url, json=payload, timeout=60.0)
            response.raise_for_status()
            return response.json()["message"]["content"]
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            return ""

    def get_structured_completion(self, prompt: str, system_prompt: str) -> dict[str, Any]:
        """Get JSON completion from LLM."""
        # For OpenAI, we can enforce JSON mode
        if self.provider == "openai":
            try:
                response = self.client.chat.completions.create(
                    model=self.settings.openai_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                )
                content = response.choices[0].message.content or "{}"
                return json.loads(content)
            except Exception as e:
                logger.error(f"OpenAI JSON error: {e}")
                return {}
        
        # For Ollama, we rely on the prompt + format="json" in _get_ollama_completion (if refactored)
        # But for now, let's just reuse get_completion and parse manually
        content = self.get_completion(prompt, system_prompt + " Output valid JSON only.")
        try:
            # Clean potential markdown (```json ... ```)
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from LLM: {content}")
            return {}
