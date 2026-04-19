from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class HardAssertion:
    type: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class SoftAssertion:
    metric: str
    rubric: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class CaseSpec:
    id: str
    input: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    hard_assertions: list[HardAssertion] = field(default_factory=list)
    soft_assertions: list[SoftAssertion] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "CaseSpec":
        return cls(
            id=str(raw["id"]),
            input=str(raw["input"]),
            description=str(raw.get("description", "")),
            tags=[str(tag) for tag in raw.get("tags", [])],
            hard_assertions=[
                HardAssertion(
                    type=str(item["type"]),
                    params=dict(item.get("params", {})),
                )
                for item in raw.get("hard_assertions", [])
            ],
            soft_assertions=[
                SoftAssertion(
                    metric=str(item["metric"]),
                    rubric=str(item["rubric"]),
                    params=dict(item.get("params", {})),
                )
                for item in raw.get("soft_assertions", [])
            ],
            metadata=dict(raw.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "input": self.input,
            "description": self.description,
            "tags": self.tags,
            "hard_assertions": [
                {"type": item.type, "params": item.params}
                for item in self.hard_assertions
            ],
            "soft_assertions": [
                {
                    "metric": item.metric,
                    "rubric": item.rubric,
                    "params": item.params,
                }
                for item in self.soft_assertions
            ],
            "metadata": self.metadata,
        }


@dataclass
class MetricResult:
    name: str
    passed: bool | None
    score: float | None
    reason: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AttemptResult:
    case_id: str
    attempt_index: int
    trace_path: str
    trace: dict[str, Any]
    metric_results: list[MetricResult]

    @property
    def passed(self) -> bool:
        concrete = [m for m in self.metric_results if m.passed is not None]
        return bool(concrete) and all(m.passed for m in concrete)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "attempt_index": self.attempt_index,
            "trace_path": self.trace_path,
            "passed": self.passed,
            "metric_results": [m.to_dict() for m in self.metric_results],
        }


@dataclass
class CaseRunSummary:
    case_id: str
    description: str
    tags: list[str]
    spec: dict[str, Any]
    attempts: list[AttemptResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "description": self.description,
            "tags": self.tags,
            "spec": self.spec,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
        }
