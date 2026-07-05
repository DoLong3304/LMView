"""
Output guard — validates and sanitizes LLM responses before returning to users.

Checks for:
- Financial advice or guaranteed predictions
- Unsafe content
- Response contract compliance
- Data caveat inclusion
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional

from backend.services.ai import metrics as ai_metrics

logger = logging.getLogger("ai_service.safety.output_guard")

# Patterns that indicate unsafe financial claims
_UNSAFE_PATTERNS = [
    re.compile(r"\b(guaranteed|100%|certain to|will definitely|must buy|must sell)\b", re.IGNORECASE),
    re.compile(r"\b(you should (buy|sell|trade|invest))\b", re.IGNORECASE),
    re.compile(r"\b(auto[-\s]?trad(e|ing))\b", re.IGNORECASE),
    re.compile(r"\b(execute\s+trade|place\s+order|open\s+position)\b", re.IGNORECASE),
]

# Patterns indicating code/command execution
_CODE_PATTERNS = [
    re.compile(r"```(python|javascript|sql|bash|shell|sh)\b.*?```", re.DOTALL | re.IGNORECASE),
    re.compile(r"\b(SELECT\s+\*\s+FROM|DROP\s+TABLE|DELETE\s+FROM)\b", re.IGNORECASE),
    re.compile(r"\b(eval\(|exec\(|os\.system|subprocess)\b", re.IGNORECASE),
]

# Required disclaimer keywords. Keep this list substantive: generic words like
# "risk" are common in analysis but are not, by themselves, disclaimers.
_DISCLAIMER_KEYWORDS = [
    "not financial advice",
    "educational purposes",
    "for educational",
    "disclaimer",
    "not a recommendation",
    "do your own research",
    "dyor",
    "not a financial advisor",
    "cannot provide financial advice",
    "can't provide financial",
    "không phải lời khuyên tài chính",
    "chỉ mang tính giáo dục",
    "tự nghiên cứu",
]

DISCLAIMER_TEXT = (
    "\n\n⚠️ *This analysis is for educational purposes only and does not constitute "
    "financial advice. Cryptocurrency trading carries significant risk. "
    "Always do your own research before making any trading decisions.*"
)

DISCLAIMER_TEXT_VI = (
    "\n\n⚠️ *Phân tích này chỉ mang tính giáo dục và không phải lời khuyên tài chính. "
    "Giao dịch tiền điện tử có rủi ro đáng kể. "
    "Luôn tự nghiên cứu trước khi đưa ra quyết định giao dịch.*"
)


def guard_output(
    content: str,
    language: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate and sanitize LLM output.

    Returns:
        Dict with:
        - content: sanitized content string
        - warnings: list of warning messages
        - blocked: True if content was fully blocked
        - disclaimer_added: True if disclaimer was appended
    """
    start = time.monotonic()
    warnings: List[str] = []
    blocked = False
    disclaimer_added = False

    # Check for unsafe financial claims
    for pattern in _UNSAFE_PATTERNS:
        if pattern.search(content):
            warnings.append(
                f"Response contained potentially unsafe financial claim "
                f"(matched: {pattern.pattern[:40]})"
            )
            ai_metrics.record_output_guard_flag(
                flag_type="unsafe_financial_claim",
                severity="warning",
            )
            # Don't block, but add a strong caveat
            content = re.sub(
                pattern,
                lambda m: f"⚠️ [{m.group(0)}]",
                content,
            )

    # Check for code execution
    for pattern in _CODE_PATTERNS:
        if pattern.search(content):
            warnings.append("Response contained code execution patterns — removed")
            ai_metrics.record_output_guard_flag(
                flag_type="code_execution",
                severity="warning",
            )
            content = re.sub(pattern, "[code removed for safety]", content)

    # Ensure disclaimer is present
    has_disclaimer = any(
        kw.lower() in content.lower() for kw in _DISCLAIMER_KEYWORDS
    )

    if not has_disclaimer:
        if language and language.lower() in ("vi", "vietnamese"):
            content += DISCLAIMER_TEXT_VI
        else:
            content += DISCLAIMER_TEXT
        disclaimer_added = True

    # Record latency (B13 observability).
    ai_metrics.AI_OUTPUT_GUARD_LATENCY.observe(time.monotonic() - start)

    return {
        "content": content,
        "warnings": warnings,
        "blocked": blocked,
        "disclaimer_added": disclaimer_added,
    }
