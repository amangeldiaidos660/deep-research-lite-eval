from __future__ import annotations

from typing import Protocol

from eval_framework.judge import JudgeClient
from eval_framework.schema import CaseSpec, MetricResult


class Metric(Protocol):
    name: str

    def evaluate(
        self,
        *,
        case: CaseSpec,
        trace: dict,
        judge: JudgeClient,
    ) -> MetricResult: ...


class MetricRegistry:
    def __init__(self) -> None:
        self._metrics: dict[str, Metric] = {}

    def register(self, metric: Metric) -> None:
        self._metrics[metric.name] = metric

    def get(self, name: str) -> Metric:
        return self._metrics[name]

    def names(self) -> list[str]:
        return sorted(self._metrics)

