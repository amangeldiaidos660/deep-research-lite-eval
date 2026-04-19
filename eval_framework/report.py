from __future__ import annotations

import math
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from eval_framework.pricing import effective_cost_usd
from eval_framework.schema import CaseRunSummary


def build_suite_summary(
    *,
    cases: list[CaseRunSummary],
    repeats: int,
    reliability_k: int = 3,
) -> dict[str, Any]:
    attempts = [attempt for case in cases for attempt in case.attempts]
    passed_attempts = [attempt for attempt in attempts if attempt.passed]
    wall_times = [attempt.trace.get("wall_time_ms", 0) for attempt in attempts]
    costs = [effective_cost_usd(attempt.trace) for attempt in attempts]
    tool_counts = [
        sum(len(message.get("tool_calls", [])) for message in attempt.trace.get("messages", []) if message.get("role") == "assistant")
        for attempt in attempts
    ]

    case_summaries = []
    for case in cases:
        pass_count = sum(1 for attempt in case.attempts if attempt.passed)
        rate = pass_count / len(case.attempts) if case.attempts else 0.0
        per_case_wall_times = [attempt.trace.get("wall_time_ms", 0) for attempt in case.attempts]
        per_case_costs = [effective_cost_usd(attempt.trace) for attempt in case.attempts]
        per_case_tool_counts = [
            sum(
                len(message.get("tool_calls", []))
                for message in attempt.trace.get("messages", [])
                if message.get("role") == "assistant"
            )
            for attempt in case.attempts
        ]
        case_summaries.append(
            {
                "case_id": case.case_id,
                "description": case.description,
                "tags": case.tags,
                "spec": case.spec,
                "pass_count": pass_count,
                "attempts": len(case.attempts),
                "pass_rate": round(rate, 4),
                "pass_pow_k": round(rate**reliability_k, 4),
                "latency_stddev_ms": round(pstdev(per_case_wall_times), 2) if len(per_case_wall_times) > 1 else 0.0,
                "cost_stddev_usd": round(pstdev(per_case_costs), 6) if len(per_case_costs) > 1 else 0.0,
                "tool_calls_stddev": round(pstdev(per_case_tool_counts), 2) if len(per_case_tool_counts) > 1 else 0.0,
                "attempt_results": [
                    attempt.to_dict(include_trace=True) for attempt in case.attempts
                ],
            }
        )

    return {
        "repeats": repeats,
        "reliability_k": reliability_k,
        "aggregate": {
            "case_count": len(cases),
            "attempt_count": len(attempts),
            "attempt_pass_rate": round(len(passed_attempts) / len(attempts), 4) if attempts else 0.0,
            "total_cost_usd": round(sum(costs), 6),
            "mean_tool_calls_per_attempt": round(mean(tool_counts), 2) if tool_counts else 0.0,
            "p50_latency_ms": _percentile(wall_times, 50),
            "p95_latency_ms": _percentile(wall_times, 95),
            "latency_stddev_ms": round(pstdev(wall_times), 2) if len(wall_times) > 1 else 0.0,
            "cost_stddev_usd": round(pstdev(costs), 6) if len(costs) > 1 else 0.0,
            "tool_calls_stddev": round(pstdev(tool_counts), 2) if len(tool_counts) > 1 else 0.0,
        },
        "cases": case_summaries,
    }


def render_markdown(summary: dict[str, Any], output_path: str | Path) -> None:
    lines = [
        "# Evaluation Run Summary",
        "",
        f"- Cases: {summary['aggregate']['case_count']}",
        f"- Attempts: {summary['aggregate']['attempt_count']}",
        f"- Attempt pass rate: {summary['aggregate']['attempt_pass_rate']}",
        f"- Total cost (USD): {summary['aggregate']['total_cost_usd']}",
        f"- p50 latency (ms): {summary['aggregate']['p50_latency_ms']}",
        f"- p95 latency (ms): {summary['aggregate']['p95_latency_ms']}",
        f"- Latency stddev (ms): {summary['aggregate']['latency_stddev_ms']}",
        f"- Cost stddev (USD): {summary['aggregate']['cost_stddev_usd']}",
        f"- Mean tool calls / attempt: {summary['aggregate']['mean_tool_calls_per_attempt']}",
        f"- Tool calls stddev: {summary['aggregate']['tool_calls_stddev']}",
        "",
        "## Per Case",
        "",
    ]
    for case in summary["cases"]:
        lines.append(
            f"- `{case['case_id']}`: {case['pass_count']}/{case['attempts']} passed "
            f"(pass rate={case['pass_rate']}, pass^{summary['reliability_k']}={case['pass_pow_k']}, "
            f"latency stddev={case['latency_stddev_ms']}, tool stddev={case['tool_calls_stddev']})"
        )
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")


def build_diff(current: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    previous_cases = {item["case_id"]: item for item in previous.get("cases", [])}
    regressions: list[dict[str, Any]] = []
    improvements: list[dict[str, Any]] = []
    added_cases: list[dict[str, Any]] = []
    removed_cases: list[dict[str, Any]] = []

    for item in current.get("cases", []):
        prior = previous_cases.get(item["case_id"])
        if prior is None:
            added_cases.append({"case_id": item["case_id"], "current_pass_rate": item["pass_rate"]})
            continue
        delta = item["pass_rate"] - prior.get("pass_rate", 0.0)
        payload = {
            "case_id": item["case_id"],
            "current_pass_rate": item["pass_rate"],
            "previous_pass_rate": prior.get("pass_rate", 0.0),
            "delta": round(delta, 4),
        }
        if delta < 0:
            regressions.append(payload)
        elif delta > 0:
            improvements.append(payload)

    current_case_ids = {item["case_id"] for item in current.get("cases", [])}
    for item in previous.get("cases", []):
        if item["case_id"] not in current_case_ids:
            removed_cases.append(
                {"case_id": item["case_id"], "previous_pass_rate": item.get("pass_rate", 0.0)}
            )

    return {
        "aggregate": {
            "attempt_pass_rate_delta": round(
                current.get("aggregate", {}).get("attempt_pass_rate", 0.0)
                - previous.get("aggregate", {}).get("attempt_pass_rate", 0.0),
                4,
            ),
            "total_cost_delta_usd": round(
                current.get("aggregate", {}).get("total_cost_usd", 0.0)
                - previous.get("aggregate", {}).get("total_cost_usd", 0.0),
                6,
            ),
            "p95_latency_delta_ms": round(
                current.get("aggregate", {}).get("p95_latency_ms", 0.0)
                - previous.get("aggregate", {}).get("p95_latency_ms", 0.0),
                2,
            ),
        },
        "regressions": regressions,
        "improvements": improvements,
        "added_cases": added_cases,
        "removed_cases": removed_cases,
    }


def _percentile(values: list[float], pct: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(v) for v in values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (pct / 100) * (len(ordered) - 1)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return round(ordered[lower], 2)
    weight = rank - lower
    return round(ordered[lower] * (1 - weight) + ordered[upper] * weight, 2)
