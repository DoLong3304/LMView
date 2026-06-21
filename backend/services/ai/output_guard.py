"""Compatibility wrapper for AI output guard.

Re-exports ``ai_service.safety.output_guard`` functions.
"""
from ai_service.safety.output_guard import guard_output

__all__ = ["guard_output"]
