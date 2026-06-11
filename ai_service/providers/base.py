"""
Base provider interface for LLM completions.

All provider implementations must implement this interface.
The system does not care whether the underlying model is local vLLM,
online API, or the none fallback - the contract is the same.
"""
from __future__ import annotations

import abc
import logging
from typing import Any, Dict, List, Optional

from backend.models.ai.providers import (
    LLMCompletionRequest,
    LLMCompletionResponse,
    ProviderHealthStatus,
    ProviderInfo,
    ProviderType,
)

logger = logging.getLogger("ai_service.providers.base")


class BaseProvider(abc.ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, provider_name: str, model_name: Optional[str] = None):
        self.provider_name = provider_name
        self.model_name = model_name

    @abc.abstractmethod
    async def generate_chat_completion(
        self,
        request: LLMCompletionRequest,
    ) -> LLMCompletionResponse:
        """Generate a chat completion response."""
        ...

    async def generate_structured_response(
        self,
        request: LLMCompletionRequest,
    ) -> LLMCompletionResponse:
        """
        Generate a structured (JSON-mode) response.

        Default implementation falls back to regular chat completion.
        Providers that support native structured output should override this.
        """
        return await self.generate_chat_completion(request)

    @abc.abstractmethod
    async def health_check(self) -> ProviderHealthStatus:
        """Check if this provider is available and healthy."""
        ...

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for a string.

        Default uses a rough 4-chars-per-token heuristic.
        Providers may override with tiktoken or model-specific tokenizers.
        """
        return max(1, len(text) // 4)

    def get_info(self) -> ProviderInfo:
        """Return provider metadata."""
        return ProviderInfo(
            provider_name=self.provider_name,
            provider_type=ProviderType.NONE,
            model_name=self.model_name,
            is_local=False,
            is_available=False,
        )
