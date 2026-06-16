"""
AI model sub-package — Pydantic schemas for AI chat, providers, RAG, and evaluation.

Re-exports all Phase 0 models for backward compatibility.
"""
from backend.models.ai.chat import (
    AIChatMode,
    AIChatRequest,
    AIChatResponse,
    AIMessageRole,
    AISessionCreateRequest,
    AISessionResponse,
    AIMessageResponse,
)
from backend.models.ai.chart_actions import (
    AIChartAction,
    AIChartActionRecordRequest,
    AIChartActionType,
    AIChartActionValidateRequest,
    AIChartActionValidationResult,
)
from backend.models.ai.common import (
    AIHealthResponse,
    ScopeCategory,
    ScopeGateResult,
)
from backend.models.ai.providers import (
    ProviderInfo,
    ProviderHealthStatus,
    ProviderRoutingResult,
    LLMCompletionRequest,
    LLMCompletionResponse,
)
from backend.models.ai.rag import (
    RAGChunkResult,
    RAGRetrievalRequest,
    RAGRetrievalResponse,
    RAGRetrievalWarning,
)
from backend.models.ai.knowledge import (
    KnowledgeSourceMeta,
    KnowledgeDocumentMeta,
    KnowledgeIngestRequest,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from backend.models.ai.evals import (
    GoldenQuestion,
    EvalResult,
    EvalSuiteResult,
)
from backend.models.ai.agents import (
    AgentExecutionSummary,
    ExpertRunSummary,
    AgentExecutionDetail,
)

__all__ = [
    # Chat / Session
    "AIChatMode",
    "AIChatRequest",
    "AIChatResponse",
    "AIMessageRole",
    "AISessionCreateRequest",
    "AISessionResponse",
    "AIMessageResponse",
    # Chart actions
    "AIChartAction",
    "AIChartActionRecordRequest",
    "AIChartActionType",
    "AIChartActionValidateRequest",
    "AIChartActionValidationResult",
    # Common
    "AIHealthResponse",
    "ScopeCategory",
    "ScopeGateResult",
    # Providers
    "ProviderInfo",
    "ProviderHealthStatus",
    "ProviderRoutingResult",
    "LLMCompletionRequest",
    "LLMCompletionResponse",
    # RAG
    "RAGChunkResult",
    "RAGRetrievalRequest",
    "RAGRetrievalResponse",
    "RAGRetrievalWarning",
    # Knowledge
    "KnowledgeSourceMeta",
    "KnowledgeDocumentMeta",
    "KnowledgeIngestRequest",
    "KnowledgeSearchRequest",
    "KnowledgeSearchResponse",
    # Evals
    "GoldenQuestion",
    "EvalResult",
    "EvalSuiteResult",
    # Agents
    "AgentExecutionSummary",
    "ExpertRunSummary",
    "AgentExecutionDetail",
]
