"""Execution persistence — stores agent traces in PostgreSQL.

Records agent execution metadata, expert run logs, and performance metrics
for observability and debugging.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ai_service.agents.state import AgentState
from ai_service.agents.types import ExpertOutput

logger = logging.getLogger("ai_service.agents.persistence")


async def store_execution(state: AgentState) -> Optional[str]:
    """Store agent execution trace in PostgreSQL.

    Returns the execution_id or None if storage failed.
    """
    try:
        from backend.core.postgres import get_pg_pool
        pool = await get_pg_pool()
        if not pool:
            logger.warning("PostgreSQL pool not available for agent execution storage.")
            return None

        intent = state.get("intent")
        token_usage = state.get("token_usage", {})
        routing = state.get("provider_routing", {})

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO ai_agent_executions (
                    session_id, user_id, query, mode, intent,
                    activated_experts, total_latency_ms,
                    total_token_input, total_token_output,
                    estimated_cost_usd, confidence, revision_count,
                    orchestration_mode, provider, model_name,
                    data_caveats, warnings
                ) VALUES (
                    $1::uuid, $2::uuid, $3, $4, $5,
                    $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17
                ) RETURNING id
                """,
                state.get("session_id"),
                state.get("user_id"),
                state.get("user_query", "")[:4000],
                state.get("mode", "ask"),
                intent.primary_intent.value if intent else None,
                state.get("activated_experts", []),
                _total_latency(state),
                token_usage.get("input", 0),
                token_usage.get("output", 0),
                state.get("estimated_cost_usd"),
                state.get("confidence", 0.5),
                state.get("revision_count", 0),
                "langgraph",
                routing.get("selected_provider"),
                routing.get("selected_model"),
                state.get("data_caveats", []),
                state.get("warnings", []),
            )

            execution_id = str(row["id"]) if row else None

            # Store individual expert runs
            if execution_id:
                await _store_expert_runs(conn, execution_id, state)

            return execution_id

    except Exception as exc:
        logger.error("Failed to store agent execution: %s", exc, exc_info=True)
        return None


async def _store_expert_runs(conn: Any, execution_id: str, state: AgentState) -> None:
    """Store individual expert run logs."""
    expert_outputs = state.get("expert_outputs", {})

    for expert_name, output in expert_outputs.items():
        if not isinstance(output, ExpertOutput):
            continue
        try:
            await conn.execute(
                """
                INSERT INTO ai_expert_runs (
                    execution_id, expert_name, latency_ms,
                    token_input, token_output, confidence,
                    output_summary, structured_data, data_sources,
                    status, error_message
                ) VALUES (
                    $1::uuid, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10, $11
                )
                """,
                execution_id,
                expert_name,
                output.latency_ms,
                output.token_usage.get("input", 0),
                output.token_usage.get("output", 0),
                output.confidence,
                output.content[:2000] if output.content else None,
                _safe_json(output.structured_data),
                output.data_sources,
                "error" if output.error else "success",
                output.error,
            )
        except Exception as exc:
            logger.warning("Failed to store expert run %s: %s", expert_name, exc)


def _total_latency(state: AgentState) -> int:
    """Calculate total latency from timing dict."""
    timing = state.get("timing", {})
    return int(sum(timing.values()))


def _safe_json(data: Dict[str, Any]) -> Optional[str]:
    """Safely serialize dict to JSON string for JSONB column."""
    if not data:
        return None
    try:
        import json
        return json.dumps(data, default=str)
    except (TypeError, ValueError):
        return None
