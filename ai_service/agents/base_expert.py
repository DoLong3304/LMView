"""Base expert interface for LangGraph DAG nodes.

All expert implementations inherit from ``BaseExpert``. The contract is:
1. Receive the full ``AgentState``.
2. Read only the fields you need.
3. Return an ``ExpertOutput`` with structured data.
4. Never call the LLM directly — data-gathering experts produce structured
   data that the synthesis node feeds into a single LLM call for best
   performance.
"""
from __future__ import annotations

import abc
import logging
from typing import Any, Dict

from ai_service.agents.state import AgentState
from ai_service.agents.types import ExpertOutput, Timer

logger = logging.getLogger("ai_service.agents.base_expert")


class BaseExpert(abc.ABC):
    """Abstract base class for all DAG expert nodes."""

    name: str = "base"

    @abc.abstractmethod
    async def execute(self, state: AgentState) -> ExpertOutput:
        """Run expert logic and return structured output.

        Args:
            state: The current graph state. Read-only from the expert's
                perspective — experts return their contribution as an
                ``ExpertOutput`` which the graph merges back.

        Returns:
            ExpertOutput with analysis content, structured data, and
            metadata.
        """
        ...

    async def safe_execute(self, state: AgentState) -> ExpertOutput:
        """Execute with error handling and timing.

        Graph nodes should call this instead of ``execute`` directly to
        get consistent error handling and latency measurement.
        """
        timer = Timer().start()
        try:
            output = await self.execute(state)
            output.latency_ms = timer.elapsed_ms()
            return output
        except Exception as exc:
            logger.error("Expert %s failed: %s", self.name, exc, exc_info=True)
            return ExpertOutput(
                expert_name=self.name,
                content="",
                error=str(exc)[:500],
                latency_ms=timer.elapsed_ms(),
                warnings=[f"Expert {self.name} encountered an error: {str(exc)[:200]}"],
            )
