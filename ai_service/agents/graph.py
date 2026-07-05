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
from ai_service.agents.types import ContextNeeds, ExpertName, ExpertOutput, IntentCategory, IntentClassification, RoutingMethod, Timer

logger = logging.getLogger("ai_service.agents.graph")

# Agent observability: node execution counter and latency histogram
# Incremented/observed by _track_node_execution below.
_NODE_COUNTERS = {"scope_gate": 0, "intent_router": 0, "expert_execution": 0, "synthesis": 0, "reflection": 0}
_NODE_LATENCIES: dict = {}

# Timeout event counters for monitoring
_TIMEOUT_EVENTS = {"intent_router": 0, "expert_execution": 0, "synthesis": 0}


def get_timeout_stats() -> dict:
    """Return timeout event counts for observability."""
    return dict(_TIMEOUT_EVENTS)


def _get_adaptive_timeout(base_seconds: float, multiplier: float = 1.5) -> float:
    """Calculate adaptive timeout based on provider health monitor.

    Uses the max recent latency from the health monitor to extend
    the base timeout during slow periods. This prevents the pipeline
    from hard-failing when the API provider is experiencing high traffic
    but still producing valid responses.

    Formula: max(base_seconds, max_recent_latency_ms / 1000 * multiplier)

    Args:
        base_seconds: Minimum timeout in seconds.
        multiplier: Safety margin over observed latency (default 1.5x).
    """
    try:
        from ai_service.providers.health import get_health_monitor
        monitor = get_health_monitor()
        all_health = monitor.get_all_health()
        max_latency = 0.0
        for _, info in all_health.items():
            lat = info.get("last_latency_ms")
            if lat and lat > max_latency:
                max_latency = float(lat)
        if max_latency > 0:
            proposed = max_latency / 1000 * multiplier
            timeout = max(base_seconds, proposed)
            if timeout > base_seconds:
                logger.info(
                    "Adaptive timeout extended: %.0fs (base=%.0fs, max_latency=%.0fms)",
                    timeout, base_seconds, max_latency,
                )
            return timeout
    except Exception as exc:
        logger.debug("Adaptive timeout calculation failed: %s", exc)
    return base_seconds


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
        try:
            output = await asyncio.wait_for(
                expert.safe_execute(state),
                timeout=20.0,
            )
            return name, output
        except asyncio.TimeoutError:
            _TIMEOUT_EVENTS["expert_execution"] += 1
            logger.warning("Expert '%s' timed out after 20s", name)
            return name, ExpertOutput(
                expert_name=name,
                error=f"Expert {name} timed out after 20s",
                warnings=[f"Expert {name} timed out — partial data available."],
            )

    try:
        results = await asyncio.wait_for(
            asyncio.gather(
                *(run_expert(name) for name in activated),
                return_exceptions=True,
            ),
            timeout=40.0,
        )
    except asyncio.TimeoutError:
        _TIMEOUT_EVENTS["expert_execution"] += 1
        logger.warning("Expert gather timed out after 40s")
        results = [TimeoutError(f"Expert {name} timed out") for name in activated]

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


def route_after_intent(state: AgentState) -> str:
    """Conditional edge after first LLM pass.

    The intent router now also runs LLM scope classification. If it detects
    out-of-scope content missed by the rule gate, stop before expert execution
    and synthesis to save tokens/resources.
    """
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

    from ai_service.agents.reflection import validate_response, route_after_reflection

    async def intent_router_node(state: AgentState) -> AgentState:
        """Intent router with 60s timeout for LLM fallback calls.

        Extended from 8s to 60s because:
        - DashScope workspace keys need per-key base URLs (fixed)
        - Each LLM call takes 1-3s with correct keys
        - Key rotation may try 2 keys × several models
        - We prefer accurate classification over fast fallback
        """
        timer = Timer().start()
        _track_node_execution("intent_router", 0)
        from ai_service.agents.intent_router import classify_intent
        try:
            result = await asyncio.wait_for(classify_intent(state), timeout=60.0)
        except asyncio.TimeoutError:
            _TIMEOUT_EVENTS["intent_router"] += 1
            logger.warning("Intent router timed out after 60s — using rule/context fallback")
            from ai_service.agents.intent_router import _default_context_needs, _rule_based_classify

            fallback_intent = _rule_based_classify(
                state.get("user_query", ""),
                state.get("mode", "ask"),
                state.get("chart_context"),
            )
            if state.get("mode") == "interact" and ExpertName.CHART_INTERACTION not in fallback_intent.activated_experts:
                fallback_intent.activated_experts.append(ExpertName.CHART_INTERACTION)
            fallback_context = _default_context_needs(
                state.get("user_query", ""),
                fallback_intent,
                state.get("chart_context"),
            )
            result = {
                "intent": fallback_intent,
                "activated_experts": [e.value for e in fallback_intent.activated_experts],
                "context_needs": fallback_context,
                "warning": ["Intent classification timed out — using rule/context fallback."],
            }
        elapsed_ms = timer.elapsed_ms()
        timing = dict(state.get("timing", {}))
        timing["intent_router"] = elapsed_ms
        _track_node_execution("intent_router", elapsed_ms)
        return result

    async def synthesis_node(state: AgentState) -> AgentState:
        """Synthesis with adaptive timeout (90s base, extends if provider slow).

        Timeout adapts to recent provider latency via health monitor.
        On timeout, assembles a best-effort response from expert outputs
        instead of returning a hard failure message.
        """
        timer = Timer().start()
        _track_node_execution("synthesis", 0)
        from ai_service.agents.synthesis import synthesize_response

        timeout = _get_adaptive_timeout(base_seconds=90.0, multiplier=1.5)
        try:
            result = await asyncio.wait_for(
                synthesize_response(state), timeout=timeout,
            )
        except asyncio.TimeoutError:
            _TIMEOUT_EVENTS["synthesis"] += 1
            logger.warning(
                "Synthesis timed out after %.0fs (adaptive). Building best-effort response.",
                timeout,
            )
            # Build best-effort response from expert outputs
            expert_outputs = state.get("expert_outputs", {})
            content_parts = []
            for name, output in expert_outputs.items():
                if output and output.content and not output.error:
                    # Extract first sentence of each expert as summary
                    first_sentence = output.content.split(".")[0]
                    if first_sentence:
                        content_parts.append(f"**{name.replace('_', ' ').title()}**: {first_sentence}.")
            if content_parts:
                response_content = (
                    "The analysis took longer than expected. Here's what I gathered so far:\n\n"
                    + "\n\n".join(content_parts)
                    + "\n\n---\n*Note: The full LLM synthesis timed out. "
                    "Please try asking a simpler or more specific question for a complete analysis.*"
                )
            else:
                response_content = (
                    "The analysis took longer than expected. "
                    "Please try asking a simpler or more specific question."
                )
            warnings = list(state.get("warnings", []))
            warnings.append(f"LLM response generation timed out after {timeout:.0f}s.")
            result = {
                "response_content": response_content,
                "warnings": warnings,
                "response_generated": True,
            }
        elapsed_ms = timer.elapsed_ms()
        timing = dict(state.get("timing", {}))
        timing["synthesis"] = elapsed_ms
        _track_node_execution("synthesis", elapsed_ms)
        return result

    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("scope_gate", scope_gate_node)
    graph.add_node("intent_router", intent_router_node)
    graph.add_node("expert_execution", expert_execution_node)
    graph.add_node("synthesis", synthesis_node)
    graph.add_node("reflection", validate_response)

    # Entry point
    graph.set_entry_point("scope_gate")

    # Scope gate → intent router or early exit
    graph.add_conditional_edges("scope_gate", route_after_scope, {
        "out_of_scope": END,
        "in_scope": "intent_router",
    })

    # Intent router → expert execution or early exit if first LLM pass found OOS
    graph.add_conditional_edges("intent_router", route_after_intent, {
        "out_of_scope": END,
        "in_scope": "expert_execution",
    })

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
