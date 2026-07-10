"""
Prompt injection detection guard.

Scans user-provided content for common prompt injection and jailbreak
patterns before sending to the LLM. Multiple detection strategies are
applied in sequence for defense-in-depth.
"""

from __future__ import annotations

import re
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Injection Pattern Libraries ───────────────────────────────────────────────

# Direct system prompt override attempts
SYSTEM_PROMPT_OVERRIDE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions|directions|prompts)", re.IGNORECASE),
    re.compile(r"forget\s+(all\s+)?(previous|above|prior)\s+(instructions|directions|prompts)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|above|prior)\s+(instructions|directions|prompts)", re.IGNORECASE),
    re.compile(r"system\s*(prompt|message|instruction)", re.IGNORECASE),
]

# Jailbreak and role-play attempts
JAILBREAK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(you(\s+are)?\s+)?now\s+(acting\s+as|you\s+are)?\s*(dan|jailbreak)", re.IGNORECASE),
    re.compile(r"\byou(\s+are)?\s+now\s+dan\b", re.IGNORECASE),
    re.compile(r"do\s+(not\s+)?(have\s+)?(any\s+)?(restrictions|limitations|boundaries|rules)", re.IGNORECASE),
    re.compile(r"output\s+(in\s+)?(raw|unfiltered|uncensored)", re.IGNORECASE),
    re.compile(r"no\s+(filter|restriction|rule|limit|boundary|censorship)", re.IGNORECASE),
    re.compile(r"bypass\s+(the\s+)?(filter|restriction|safety|guardrail)", re.IGNORECASE),
]

# Instruction manipulation attempts
INSTRUCTION_MANIPULATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"repeat\s+(the\s+)?(above|previous|entire)\s+(text|prompt|message|instruction)", re.IGNORECASE),
    re.compile(r"print\s+(the\s+)?(system\s+)?prompt", re.IGNORECASE),
    re.compile(r"show\s+(me\s+)?(the\s+)?(system\s+)?(prompt|instructions)", re.IGNORECASE),
    re.compile(r"what\s+(is|are|were)\s+(my|the)\s+(system\s+)?prompt", re.IGNORECASE),
    re.compile(r"reveal\s+(your|the)\s+(system\s+)?prompt", re.IGNORECASE),
    re.compile(r"leak\s+(your|the|system)\s+(prompt|instructions)", re.IGNORECASE),
]

# Delimiter injection attempts
DELIMITER_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"-{3,}|\*{3,}|/{3,}", re.IGNORECASE),
]

# Combined pattern set
ALL_PATTERNS: list[tuple[str, list[re.Pattern[str]]]] = [
    ("system_prompt_override", SYSTEM_PROMPT_OVERRIDE_PATTERNS),
    ("jailbreak", JAILBREAK_PATTERNS),
    ("instruction_manipulation", INSTRUCTION_MANIPULATION_PATTERNS),
    ("delimiter_injection", DELIMITER_INJECTION_PATTERNS),
]


class InjectionDetectionResult:
    """Result of injection detection scan."""

    def __init__(self) -> None:
        self.is_injection: bool = False
        self.matched_patterns: list[dict[str, Any]] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_injection": self.is_injection,
            "matched_patterns": self.matched_patterns,
        }


def scan_for_injection(text: str) -> InjectionDetectionResult:
    """
    Scan text for prompt injection patterns.

    Args:
        text: The user-provided text to scan.

    Returns:
        InjectionDetectionResult with scan findings.
    """
    result = InjectionDetectionResult()

    if not text:
        return result

    for category, patterns in ALL_PATTERNS:
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                result.is_injection = True
                matched_text = match.group(0)[:100]
                result.matched_patterns.append({
                    "category": category,
                    "pattern": pattern.pattern[:80],
                    "matched": matched_text,
                    "position": match.start(),
                })
                logger.warning(
                    "Prompt injection pattern detected",
                    category=category,
                    matched=matched_text,
                )

    return result


def validate_input(text: str, max_length: int | None = None) -> None:
    """
    Validate user input for AI processing.

    Raises:
        ValueError: If injection is detected or input exceeds max length.
    """
    if not text or not text.strip():
        raise ValueError("Input text cannot be empty")

    if max_length and len(text) > max_length:
        raise ValueError(
            f"Input text exceeds maximum length of {max_length} characters "
            f"({len(text)} provided)"
        )

    result = scan_for_injection(text)
    if result.is_injection:
        categories = {m["category"] for m in result.matched_patterns}
        raise ValueError(
            f"Prompt injection detected: matched patterns in categories: "
            f"{', '.join(sorted(categories))}"
        )


def sanitize_for_logging(text: str, max_len: int = 500) -> str:
    """Truncate and sanitize text for safe logging (prevents secrets leakage)."""
    sanitized = text.replace("\n", " ").replace("\r", " ")
    if len(sanitized) > max_len:
        sanitized = sanitized[:max_len] + "..."
    return sanitized
