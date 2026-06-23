"""
Pydantic models for LLM provider abstraction and routing.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    """Supported provider types."""
    LOCAL = "local"
    API = "api"
    NONE = "none"


class ProviderInfo(BaseModel):
    """Metadata about a configured provider."""
    provider_name: str
    provider_type: ProviderType
    model_name: Optional[str] = None
    is_local: bool = False
    is_available: bool = False
    priority: int = 0
    max_context_tokens: Optional[int] = None
    supports_structured_output: bool = False
    supports_streaming: bool = False
    base_url: Optional[str] = None


class ProviderHealthStatus(BaseModel):
    """Health check result for a single provider."""
    provider_name: str
    is_healthy: bool = False
    latency_ms: Optional[int] = None
    model_loaded: bool = False
    error: Optional[str] = None
    checked_at: Optional[datetime] = None


class ProviderRoutingResult(BaseModel):
    """Result of provider selection/routing."""
    selected_provider: Optional[str] = None
    selected_model: Optional[str] = None
    is_local: bool = False
    is_mock: bool = False
    fallback_used: bool = False
    providers_tried: List[str] = Field(default_factory=list)
    providers_failed: List[str] = Field(default_factory=list)
    routing_reason: str = ""


class LLMMessage(BaseModel):
    """A single message in a chat completion request."""
    role: str
    content: str
    name: Optional[str] = None


class LLMToolCall(BaseModel):
    """A tool call proposed by the LLM."""
    id: Optional[str] = None
    type: str = "function"
    function: Dict[str, Any] = Field(default_factory=dict)

class LLMToolFunction(BaseModel):
    """OpenAI-compatible tool definition."""
    name: str
    description: str = ""
    parameters: Dict[str, Any] = Field(default_factory=dict)

class LLMTool(BaseModel):
    """OpenAI-compatible tool spec."""
    type: str = "function"
    function: LLMToolFunction

class LLMCompletionRequest(BaseModel):
    """Request to generate a chat completion via any provider."""
    messages: List[LLMMessage]
    model: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 2048
    top_p: float = 0.95
    stop: Optional[List[str]] = None
    response_format: Optional[Dict[str, Any]] = None
    tools: Optional[List[LLMTool]] = None
    tool_choice: Optional[str] = None  # "auto", "none", "required"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LLMCompletionResponse(BaseModel):
    """Response from a chat completion request."""
    content: str
    provider: str
    model_name: Optional[str] = None
    is_mock: bool = False
    finish_reason: Optional[str] = None
    token_input: Optional[int] = None
    token_output: Optional[int] = None
    latency_ms: Optional[int] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
