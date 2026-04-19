from __future__ import annotations

from statistics import mean

from eval_framework.judge import JudgeClient
from eval_framework.schema import CaseSpec, MetricResult
from eval_framework.trace_utils import tool_names


class EfficiencyMetric:
    name = "efficiency"

    def evaluate(
        self,
        *,
        case: CaseSpec,
        trace: dict,
        judge: JudgeClient,
    ) -> MetricResult:
        del case, judge
        latencies = [
            int(message.get("latency_ms", 0))
            for message in trace.get("messages", [])
            if "latency_ms" in message
        ]
        total_tool_calls = len(tool_names(trace))
        wall_time_ms = int(trace.get("wall_time_ms", 0))
        cost = float(trace.get("cost_usd", 0.0))
        tokens = trace.get("total_tokens", {})
        details = {
            "wall_time_ms": wall_time_ms,
            "cost_usd": cost,
            "total_tool_calls": total_tool_calls,
            "mean_step_latency_ms": round(mean(latencies), 2) if latencies else 0.0,
            "input_tokens": int(tokens.get("input", 0)),
            "output_tokens": int(tokens.get("output", 0)),
        }
        return MetricResult(
            name=self.name,
            passed=True,
            score=1.0,
            reason="efficiency metrics captured",
            details=details,
        )

