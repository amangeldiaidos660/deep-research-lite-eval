from __future__ import annotations

from typing import Any


_PRICING_PER_MTOK: dict[str, dict[str, float]] = {
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
}


def normalize_model_name(model: str) -> str:
    raw = (model or "").strip()
    if raw in _PRICING_PER_MTOK:
        return raw

    parts = raw.split("-")
    if len(parts) >= 4 and parts[-1].isdigit():
        candidate = "-".join(parts[:-1])
        if candidate in _PRICING_PER_MTOK:
            return candidate
    return raw


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = _PRICING_PER_MTOK.get(normalize_model_name(model))
    if pricing is None:
        return 0.0
    return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000


def effective_cost_usd(trace: dict[str, Any]) -> float:
    recorded = float(trace.get("cost_usd", 0.0) or 0.0)
    if recorded > 0:
        return recorded
    tokens = trace.get("total_tokens", {}) or {}
    return estimate_cost_usd(
        str(trace.get("model", "")),
        int(tokens.get("input", 0) or 0),
        int(tokens.get("output", 0) or 0),
    )


def cost_details(trace: dict[str, Any]) -> dict[str, Any]:
    tokens = trace.get("total_tokens", {}) or {}
    model = str(trace.get("model", ""))
    normalized = normalize_model_name(model)
    recorded = float(trace.get("cost_usd", 0.0) or 0.0)
    effective = effective_cost_usd(trace)
    return {
        "model": model,
        "normalized_model": normalized,
        "recorded_cost_usd": recorded,
        "effective_cost_usd": round(effective, 6),
        "cost_source": "trace" if recorded > 0 else "estimated_from_tokens",
        "input_tokens": int(tokens.get("input", 0) or 0),
        "output_tokens": int(tokens.get("output", 0) or 0),
    }
