"""Compatibility wrapper for AI prompt builder.

Re-exports functions from ``ai_service.prompts.prompt_builder``.
"""
from ai_service.prompts.prompt_builder import build_ask_prompt, estimate_prompt_tokens

__all__ = ["build_ask_prompt", "estimate_prompt_tokens"]
