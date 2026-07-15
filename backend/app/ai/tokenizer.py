"""
Token counting and estimation utilities.

Uses tiktoken when available for accurate OpenAI token counting,
with a character-based fallback for other providers.
"""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# Attempt to load tiktoken for accurate tokenization
tiktoken: Any = None
try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


# Character-based fallback ratios (measured empirically)
CHAR_TO_TOKEN_RATIO = 0.25  # ~4 characters per token for English
TOKEN_TO_CHAR_RATIO = 4.0


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """
    Count the number of tokens in a text string.

    Uses tiktoken for OpenAI models, falls back to character estimation.

    Args:
        text: The text to tokenize.
        model: The model name (used for tiktoken encoding selection).

    Returns:
        Estimated token count.
    """
    if not text:
        return 0

    if TIKTOKEN_AVAILABLE:
        try:
            encoding = _get_encoding(model)
            return len(encoding.encode(text))
        except Exception as exc:
            logger.debug("tiktoken failed, falling back to estimation", error=str(exc))

    # Fallback: character-based estimation
    return _estimate_tokens(text)


def _get_encoding(model: str) -> Any:
    """Get the appropriate tiktoken encoding for a model."""
    if tiktoken is None:
        raise ImportError("tiktoken is not available")

    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback to cl100k_base for newer models
        return tiktoken.get_encoding("cl100k_base")


def _estimate_tokens(text: str) -> int:
    """
    Estimate token count from character count.

    This is a rough approximation. English text averages ~4 chars/token,
    but this varies significantly by language and content type.
    """
    return max(1, int(len(text) * CHAR_TO_TOKEN_RATIO))


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str = "gpt-4o",
) -> float:
    """
    Estimate API cost for a given token usage.

    Uses approximate per-model pricing per 1K tokens.

    Args:
        input_tokens: Number of input/prompt tokens.
        output_tokens: Number of output/completion tokens.
        model: The model name for pricing lookup.

    Returns:
        Estimated cost in USD.
    """
    pricing = _get_model_pricing(model)
    input_cost = (input_tokens / 1000) * pricing["input"]
    output_cost = (output_tokens / 1000) * pricing["output"]
    return round(input_cost + output_cost, 6)


def _get_model_pricing(model: str) -> dict[str, float]:
    """Get approximate per-1K-token pricing for a model."""
    pricing_map: dict[str, dict[str, float]] = {
        "gpt-4o": {"input": 0.0025, "output": 0.01},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        "llama3": {"input": 0.0, "output": 0.0},
    }

    # Check for known models
    for known, prices in pricing_map.items():
        if known in model.lower():
            return prices

    # Default pricing (conservative estimate)
    return {"input": 0.003, "output": 0.012}


def truncate_to_token_limit(
    text: str,
    max_tokens: int,
    model: str = "gpt-4o",
) -> str:
    """
    Truncate text to fit within a token limit.

    Args:
        text: The text to truncate.
        max_tokens: Maximum allowed tokens.
        model: Model name for encoding.

    Returns:
        Truncated text that fits within the token budget.
    """
    if count_tokens(text, model) <= max_tokens:
        return text

    if TIKTOKEN_AVAILABLE:
        try:
            encoding = _get_encoding(model)
            tokens = encoding.encode(text)
            truncated_tokens = tokens[:max_tokens]
            return encoding.decode(truncated_tokens)
        except Exception:
            pass

    # Fallback: character-based truncation
    max_chars = int(max_tokens * TOKEN_TO_CHAR_RATIO)
    return text[:max_chars]
