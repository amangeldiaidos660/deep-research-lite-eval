from __future__ import annotations

from eval_framework.judge import JudgeClient
from eval_framework.schema import CaseSpec, MetricResult


class CorrectnessMetric:
    name = "correctness"

    def evaluate(
        self,
        *,
        case: CaseSpec,
        trace: dict,
        judge: JudgeClient,
    ) -> MetricResult:
        soft = next((item for item in case.soft_assertions if item.metric == self.name), None)
        if soft is None:
            return MetricResult(
                name=self.name,
                passed=None,
                score=None,
                reason="no correctness rubric declared for this case",
            )
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
            details=verdict.details,
        )

