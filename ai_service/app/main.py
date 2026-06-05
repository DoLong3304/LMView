"""
AI Service — standalone AI inference service for LMView.

Phase 1: Provides Ask Mode with RAG and provider routing.
Phase 2: Will add Interact Mode action proposal and execution.

This service can run independently from the core FastAPI backend,
or its logic can be imported directly by the backend for embedded mode.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("ai_service")

# TODO: Phase 2+ — Implement as a standalone FastAPI service with:
# - LangGraph agent graph
# - Supervisor, market context, RAG research, TA, risk reviewer, response composer agents
# - Tool registry with market data, indicator, news, chart action tools
# - Memory service backed by PostgreSQL
# - Observability and audit logging
#
# Currently, Phase 1 AI logic lives in backend/services/ai/ and is called
# directly by the core FastAPI backend. This module is scaffolded for future
# standalone deployment.
