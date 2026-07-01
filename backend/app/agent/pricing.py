"""Per-model $/token pricing, for the live cost meter.

Cache-read tokens cost ~0.1x the input rate; cache-write (creation) tokens
cost ~1.25x the input rate at the default 5-minute TTL. Source: the Claude
API pricing table (see CLAUDE.md's model choice section for why
claude-opus-4-8 is the default here).
"""

CACHE_READ_MULTIPLIER = 0.1
CACHE_WRITE_MULTIPLIER = 1.25

# USD per million tokens: (input, output)
PRICING_PER_MILLION: dict[str, tuple[float, float]] = {
    "claude-opus-4-8": (5.00, 25.00),
    "claude-opus-4-7": (5.00, 25.00),
    "claude-opus-4-6": (5.00, 25.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
}

# Unlisted/future model IDs fall back to this rather than raising — an
# investigation shouldn't crash because the pricing table is stale.
_FALLBACK_MODEL = "claude-opus-4-8"


def estimate_cost_usd(model: str, usage: dict[str, int]) -> float:
    input_price, output_price = PRICING_PER_MILLION.get(model, PRICING_PER_MILLION[_FALLBACK_MODEL])

    input_cost = usage.get("input_tokens", 0) * input_price
    output_cost = usage.get("output_tokens", 0) * output_price
    cache_read_cost = usage.get("cache_read_input_tokens", 0) * input_price * CACHE_READ_MULTIPLIER
    cache_write_cost = usage.get("cache_creation_input_tokens", 0) * input_price * CACHE_WRITE_MULTIPLIER

    return (input_cost + output_cost + cache_read_cost + cache_write_cost) / 1_000_000
