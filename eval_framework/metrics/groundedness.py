from __future__ import annotations

from eval_framework.judge import JudgeClient
from eval_framework.schema import CaseSpec, MetricResult
from eval_framework.trace_utils import fetched_texts, fetched_urls, final_answer


class GroundednessMetric:
    name = "groundedness"

    def evaluate(
        self,
        *,
        case: CaseSpec,
        trace: dict,
        judge: JudgeClient,
    ) -> MetricResult:
        citations = [str(item) for item in trace.get("citations", [])]
        fetched = fetched_urls(trace)
        unfetched = [url for url in citations if url not in fetched]
        details = {
            "citations": citations,
            "fetched_urls": fetched,
            "supporting_texts": fetched_texts(trace),
        }
        if unfetched:
            return MetricResult(
                name=self.name,
                passed=False,
                score=0.0,
                reason="citations include URLs that were never fetched",
                details={**details, "unfetched_citations": unfetched},
            )

        soft = next((item for item in case.soft_assertions if item.metric == self.name), None)
        if soft is None:
            return MetricResult(
                name=self.name,
                passed=None,
                score=None,
                reason="hard groundedness checks passed; no judge rubric configured",
                details=details,
            )

        verdict = judge.evaluate(
            metric_name=self.name,
            rubric=soft.rubric,
            case_input=case.input,
            trace={
                **trace,
                "fetched_supporting_texts": fetched_texts(trace),
                "final_answer": final_answer(trace),
            },
            params=soft.params,
        )
        return MetricResult(
            name=self.name,
            passed=verdict.passed,
            score=verdict.score,
            reason=verdict.rationale,
            details={**details, **verdict.details},
        )

