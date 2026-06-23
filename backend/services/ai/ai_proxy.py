"""AI service proxy client.

Provides thin async HTTP wrapper around standalone AI service.
If ``AI_SERVICE_EMBEDDED`` env var is ``true`` (default), calls local
``ai_service.core.orchestrator.run_chat`` directly.  Otherwise performs
HTTP request to ``AI_SERVICE_URL``.

The proxy forwards the caller's JWT (``Authorization: Bearer ...``) to the
standalone AI service so that ``get_current_user`` on the ai-service side
can authenticate the same way it did in-process. ``X-User-ID`` is also
sent for belt-and-braces (some deployments strip the Authorization header
at the edge).

Also provides ``chat_stream`` for SSE streaming responses.
"""
from __future__ import annotations

import json
import os
from typing import AsyncGenerator, Optional

import httpx
from fastapi import Request

from backend.models.ai.chat import AIChatRequest, AIChatResponse
from ai_service.core.orchestrator import run_chat as embedded_run_chat
from ai_service.core.orchestrator import run_chat_stream as embedded_run_chat_stream

AI_SERVICE_EMBEDDED = os.getenv("AI_SERVICE_EMBEDDED", "true").lower() == "true"
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai-service:8100")


async def chat(
    body: AIChatRequest,
    user_id: str,
    request: Optional[Request] = None,
) -> AIChatResponse:
    """Send chat request.

    Embedded mode: direct call to ``ai_service.core.orchestrator.run_chat``.
    Proxy mode: POST to ``{AI_SERVICE_URL}/ai/chat`` with the same payload
    and the caller's Authorization header forwarded.
    """
    if AI_SERVICE_EMBEDDED:
        return await embedded_run_chat(body=body, user_id=user_id)

    forward_headers: dict[str, str] = {"X-User-ID": user_id}
    if request is not None:
        auth = request.headers.get("authorization")
        if auth:
            forward_headers["Authorization"] = auth

    # LLM calls to DashScope/Qwen routinely take 30–90s. Use a long
    # timeout so a slow LLM doesn't get cut off mid-stream.
    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(
            f"{AI_SERVICE_URL}/ai/chat",
            json=body.dict(),
            headers=forward_headers,
        )
        resp.raise_for_status()
        data = resp.json()
        return AIChatResponse(**data)


async def chat_stream(
    body: AIChatRequest,
    user_id: str,
    request: Optional[Request] = None,
) -> AsyncGenerator[str, None]:
    """Send streaming chat request.

    Embedded mode: direct call to embedded ``run_chat_stream``.
    Proxy mode: streaming GET from ``{AI_SERVICE_URL}/ai/chat/stream``.
    Yields SSE-encoded event strings.
    """
    if AI_SERVICE_EMBEDDED:
        async for event in embedded_run_chat_stream(body=body, user_id=user_id):
            yield event
        return

    forward_headers: dict[str, str] = {"X-User-ID": user_id}
    if request is not None:
        auth = request.headers.get("authorization")
        if auth:
            forward_headers["Authorization"] = auth

    async with httpx.AsyncClient(timeout=180) as client:
        async with client.stream(
            "POST",
            f"{AI_SERVICE_URL}/ai/chat/stream",
            json=body.dict(),
            headers=forward_headers,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    yield line[6:]  # strip "data: " prefix
