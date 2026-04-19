from __future__ import annotations

from eval_framework.judge import JudgeClient
from eval_framework.schema import CaseSpec, MetricResult
from eval_framework.trace_utils import tool_calls


class ToolUseMetric:
    name = "tool_use"

    def evaluate(
        self,
        *,
        case: CaseSpec,
        trace: dict,
        judge: JudgeClient,
    ) -> MetricResult:
        calls = tool_calls(trace)
        names = [call.get("name", "") for call in calls]
        if str(trace.get("stopped_reason")) == "error":
            return MetricResult(
                name=self.name,
                passed=False,
                score=0.0,
                reason="agent run ended with an execution error before valid tool usage could be assessed",
                details={"error": trace.get("error"), "tool_names": names},
            )
        search_idx = _first_index(names, "web_search")
        fetch_idx = _first_index(names, "fetch_url")
        finish_idx = _first_index(names, "finish")

        failures: list[str] = []
        if fetch_idx != -1 and search_idx == -1:
            failures.append("fetch_url was used before any web_search")
        if finish_idx != -1 and fetch_idx == -1:
            failures.append("finish was called before any fetch_url")
        if (
            search_idx != -1
            and fetch_idx != -1
            and fetch_idx < search_idx
        ):
            failures.append("fetch_url appeared before web_search")
        if (
            fetch_idx != -1
            and finish_idx != -1
            and finish_idx < fetch_idx
        ):
            failures.append("finish appeared before fetch_url")

        bad_args: list[str] = []
        for call in calls:
            if not isinstance(call.get("args"), dict):
                bad_args.append(f"{call.get('name')}: non-object args")
        if bad_args:
            failures.append("invalid tool arguments observed")

        soft = next((item for item in case.soft_assertions if item.metric == self.name), None)
        if not failures and soft is not None:
            verdict = judge.evaluate(
                metric_name=self.name,
                rubric=soft.rubric,
                case_input=case.input,
                trace=trace,
                params=soft.params,
            )
            return MetricResult(
                name=self.name,
                passed=verdict.passed,
                score=verdict.score,
                reason=verdict.rationale,
                details={**verdict.details, "tool_names": names, "bad_args": bad_args},
            )

        return MetricResult(
            name=self.name,
            passed=not failures,
            score=1.0 if not failures else 0.0,
            reason="tool usage ordering looks valid" if not failures else failures[0],
            details={"failures": failures, "tool_names": names, "bad_args": bad_args},
        )


def _first_index(items: list[str], target: str) -> int:
    try:
        return items.index(target)
    except ValueError:
        return -1
