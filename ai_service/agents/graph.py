"""LangGraph multi-agent DAG for LMView AI.

Compiles the full agent graph: scope_gate → intent_router → parallel experts
→ synthesis → reflection (with revision loop) → output.

The graph uses a single shared ``AgentState`` TypedDict and supports
conditional routing, parallel expert execution, and stateful resumability.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from ai_service.agents.state import AgentState
from ai_service.agents.types import ExpertName, ExpertOutput, Timer

logger = logging.getLogger("ai_service.agents.graph")

# Agent observability: node execution counter and latency histogram
# Incremented/observed by _track_node_execution below.
_NODE_COUNTERS = {"scope_gate": 0, "intent_router": 0, "expert_execution": 0, "synthesis": 0, "reflection": 0}
_NODE_LATENCIES: dict = {}


def get_node_stats() -> dict:
    """Return aggregate runtime stats for agent nodes."""
    return {
        "node_counts": dict(_NODE_COUNTERS),
        "node_latencies": {k: round(sum(v) / len(v), 2) if v else 0.0 for k, v in _NODE_LATENCIES.items()},
    }


def _track_node_execution(node_name: str, elapsed_ms: float) -> None:
    """Record node execution for observability."""
    _NODE_COUNTERS[node_name] = _NODE_COUNTERS.get(node_name, 0) + 1
    if node_name not in _NODE_LATENCIES:
        _NODE_LATENCIES[node_name] = []
    _NODE_LATENCIES[node_name].append(elapsed_ms)
    # Keep last 100 samples to bound memory
    if len(_NODE_LATENCIES[node_name]) > 100:
        _NODE_LATENCIES[node_name] = _NODE_LATENCIES[node_name][-100:]

# ── Expert registry ───────────────────────────────────────────────────────────

_EXPERT_INSTANCES: Dict[str, Any] = {}


def _get_expert(name: str) -> Any:
    """Lazy-load expert instances."""
    if name not in _EXPERT_INSTANCES:
        if name == ExpertName.TECHNICAL_ANALYSIS.value:
            from ai_service.agents.experts.technical_analysis import TechnicalAnalysisExpert
            _EXPERT_INSTANCES[name] = TechnicalAnalysisExpert()
        elif name == ExpertName.MARKET_DATA.value:
            from ai_service.agents.experts.market_data import MarketDataExpert
            _EXPERT_INSTANCES[name] = MarketDataExpert()
        elif name == ExpertName.NEWS_SENTIMENT.value:
            from ai_service.agents.experts.news_sentiment import NewsSentimentExpert
            _EXPERT_INSTANCES[name] = NewsSentimentExpert()
        elif name == ExpertName.RAG_KNOWLEDGE.value:
            from ai_service.agents.experts.rag_knowledge import RAGKnowledgeExpert
            _EXPERT_INSTANCES[name] = RAGKnowledgeExpert()
        elif name == ExpertName.CHART_INTERACTION.value:
            from ai_service.agents.experts.chart_interaction import ChartInteractionExpert
            _EXPERT_INSTANCES[name] = ChartInteractionExpert()
        elif name == ExpertName.GENERAL.value:
            from ai_service.agents.experts.general import GeneralExpert
            _EXPERT_INSTANCES[name] = GeneralExpert()
    return _EXPERT_INSTANCES.get(name)


# ── Node functions ────────────────────────────────────────────────────────────

async def scope_gate_node(state: AgentState) -> AgentState:
    """Run scope gate classification."""
    timer = Timer().start()
    _track_node_execution("scope_gate", 0)  # will update with final timing
    from ai_service.safety.scope_gate import check_scope

    user_query = state.get("user_query", "")
    scope_result = check_scope(user_query)

    # Assemble data caveats early
    from ai_service.context.context_service import assemble_data_caveats
    data_caveats = assemble_data_caveats(state.get("chart_context"))

    elapsed_ms = timer.elapsed_ms()
    timing = dict(state.get("timing", {}))
    timing["scope_gate"] = elapsed_ms
    _track_node_execution("scope_gate", elapsed_ms)

    if not scope_result.in_scope:
        return {
            "scope_in_scope": False,
            "scope_category": scope_result.category.value,
            "scope_reason": scope_result.reason,
            "scope_confidence": scope_result.confidence,
            "scope_response": (
                "I can only help with cryptocurrency market analysis, technical indicators, "
                "chart interaction, and LMView platform usage. "
                f"Reason: {scope_result.reason}"
            ),
            "data_caveats": data_caveats,
            "timing": timing,
        }

    return {
        "scope_in_scope": True,
        "scope_category": scope_result.category.value,
        "scope_reason": scope_result.reason,
        "scope_confidence": scope_result.confidence,
        "scope_response": None,
        "data_caveats": data_caveats,
        "timing": timing,
    }


async def expert_execution_node(state: AgentState) -> AgentState:
    """Execute all activated experts in parallel.

    This is the MoE (Mixture of Experts) node — only activated experts
    run, minimizing compute. Experts that gather data run concurrently
    via asyncio.gather().
    """
    timer = Timer().start()
    _track_node_execution("expert_execution", 0)
    activated = state.get("activated_experts", [])

    if not activated:
        activated = [ExpertName.GENERAL.value]

    # Run experts in parallel
    async def run_expert(name: str) -> tuple[str, ExpertOutput]:
        expert = _get_expert(name)
        if not expert:
            return name, ExpertOutput(
                expert_name=name,
                error=f"Expert {name} not found.",
                warnings=[f"Expert {name} not registered."],
            )
        output = await expert.safe_execute(state)
        return name, output

    results = await asyncio.gather(
        *(run_expert(name) for name in activated),
        return_exceptions=True,
    )

    expert_outputs: Dict[str, ExpertOutput] = {}
    rag_chunks = []
    rag_sources = []
    news_context = None
    market_data = None
    indicator_data = None
    warnings = list(state.get("warnings", []))

    for result in results:
        if isinstance(result, Exception):
            logger.error("Expert execution failed: %s", result)
            continue
        name, output = result
        expert_outputs[name] = output

        # Extract shared state from specific experts
        if name == ExpertName.RAG_KNOWLEDGE.value and output.structured_data:
            rag_chunks = output.structured_data.get("chunks", [])
            rag_sources = output.structured_data.get("sources", [])

        if name == ExpertName.NEWS_SENTIMENT.value and output.structured_data:
            news_context = output.structured_data

        if name == ExpertName.MARKET_DATA.value and output.structured_data:
            market_data = output.structured_data

        if name == ExpertName.TECHNICAL_ANALYSIS.value and output.structured_data:
            indicator_data = output.structured_data.get("indicators")

        # Collect warnings
        warnings.extend(output.warnings)

    elapsed_expert = timer.elapsed_ms()
    timing = dict(state.get("timing", {}))
    timing["expert_execution"] = elapsed_expert
    _track_node_execution("expert_execution", elapsed_expert)

    # Calculate aggregate confidence
    confidences = [o.confidence for o in expert_outputs.values() if not o.error]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.3

    # Run ensemble voting for cross-validation
    from ai_service.agents.ensemble import ensemble_vote
    ensemble_result = await ensemble_vote(expert_outputs)

    return {
        "expert_outputs": expert_outputs,
        "rag_chunks": rag_chunks,
        "rag_sources": rag_sources,
        "news_context": news_context,
        "market_data": market_data,
        "indicator_data": indicator_data,
        "warnings": warnings,
        "confidence": ensemble_result["aggregate_confidence"],
        "cross_validated_signals": ensemble_result["cross_validated_signals"],
        "conflicting_signals": ensemble_result["conflicting_signals"],
        "dominant_expert": ensemble_result["dominant_expert"],
        "timing": timing,
    }


def route_after_scope(state: AgentState) -> str:
    """Conditional edge after scope gate."""
    if state.get("scope_response") is not None:
        return "out_of_scope"
    return "in_scope"


# ── Graph compilation ─────────────────────────────────────────────────────────

_compiled_graph = None


def get_compiled_graph():
    """Get or compile the LangGraph StateGraph.

    Uses lazy compilation so the graph is only built when langgraph
    mode is first activated.
    """
    global _compiled_graph
    if _compiled_graph is not None:
        return _compiled_graph

    try:
        from langgraph.graph import StateGraph, END
    except ImportError:
        logger.error(
            "langgraph not installed. Install with: pip install langgraph langchain-core"
        )
        raise ImportError(
            "langgraph is required for AI_ORCHESTRATION=langgraph. "
            "Install with: pip install langgraph langchain-core"
        )

    from ai_service.agents.intent_router import classify_intent
    from ai_service.agents.synthesis import synthesize_response
    from ai_service.agents.reflection import validate_response, route_after_reflection

    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("scope_gate", scope_gate_node)
    graph.add_node("intent_router", classify_intent)
    graph.add_node("expert_execution", expert_execution_node)
    graph.add_node("synthesis", synthesize_response)
    graph.add_node("reflection", validate_response)

    # Entry point
    graph.set_entry_point("scope_gate")

    # Scope gate → intent router or early exit
    graph.add_conditional_edges("scope_gate", route_after_scope, {
        "out_of_scope": END,
        "in_scope": "intent_router",
    })

    # Intent router → expert execution
    graph.add_edge("intent_router", "expert_execution")

    # Expert execution → synthesis
    graph.add_edge("expert_execution", "synthesis")

    # Synthesis → reflection
    graph.add_edge("synthesis", "reflection")

    # Reflection → END (approved) or synthesis (revision)
    graph.add_conditional_edges("reflection", route_after_reflection, {
        "approved": END,
        "needs_revision": "synthesis",
    })

    _compiled_graph = graph.compile()
    logger.info("LangGraph multi-agent DAG compiled successfully.")
    return _compiled_graph


async def run_graph(initial_state: AgentState) -> AgentState:
    """Execute the compiled graph with the given initial state.

    Returns the final state after all nodes have completed.
    """
    graph = get_compiled_graph()
    result = await graph.ainvoke(initial_state)
    return result


def reset_graph() -> None:
    """Reset compiled graph for tests."""
    global _compiled_graph
    _compiled_graph = None
    _EXPERT_INSTANCES.clear()
    _NODE_COUNTERS.clear()
    _NODE_LATENCIES.clear()
