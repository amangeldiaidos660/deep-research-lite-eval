from __future__ import annotations

from eval_framework.judge import JudgeClient
from eval_framework.schema import CaseSpec, MetricResult
from eval_framework.trace_utils import fetched_urls, final_answer, tool_names


class HardAssertionsMetric:
    name = "hard_assertions"

    def evaluate(
        self,
        *,
        case: CaseSpec,
        trace: dict,
        judge: JudgeClient,
    ) -> MetricResult:
        del judge
        failures: list[str] = []
        tools = tool_names(trace)
        fetched = fetched_urls(trace)
        citations = [str(item) for item in trace.get("citations", [])]
        answer = final_answer(trace)

        for assertion in case.hard_assertions:
            params = assertion.params
            kind = assertion.type
            if kind == "stopped_reason_is":
                expected = str(params["value"])
                actual = str(trace.get("stopped_reason"))
                if actual != expected:
                    failures.append(
                        f"expected stopped_reason={expected!r}, got {actual!r}"
                    )
            elif kind == "tool_called":
                expected_tool = str(params["tool"])
                if expected_tool not in tools:
                    failures.append(f"required tool not called: {expected_tool}")
            elif kind == "tool_call_count_lte":
                limit = int(params["value"])
                if len(tools) > limit:
                    failures.append(f"tool calls {len(tools)} exceeded limit {limit}")
            elif kind == "answer_contains":
                needle = str(params["value"])
                if needle.lower() not in answer.lower():
                    failures.append(f"final answer missing required text: {needle}")
            elif kind == "answer_not_contains":
                needle = str(params["value"])
                if needle.lower() in answer.lower():
                    failures.append(f"final answer contains forbidden text: {needle}")
            elif kind == "citations_are_fetched":
                missing = [url for url in citations if url not in fetched]
                if missing:
                    failures.append(
                        "citations include unfetched URLs: " + ", ".join(missing)
                    )
            elif kind == "tool_sequence_contains":
                seq = [str(item) for item in params["value"]]
                if not _contains_subsequence(tools, seq):
                    failures.append(
                        f"required tool sequence not observed: {' -> '.join(seq)}"
                    )
            else:
                failures.append(f"unknown hard assertion type: {kind}")

        return MetricResult(
            name=self.name,
            passed=not failures,
            score=1.0 if not failures else 0.0,
            reason="all hard assertions passed" if not failures else failures[0],
            details={"failures": failures},
        )


def _contains_subsequence(items: list[str], expected: list[str]) -> bool:
    if not expected:
        return True
    idx = 0
    for item in items:
        if item == expected[idx]:
            idx += 1
            if idx == len(expected):
                return True
    return False

