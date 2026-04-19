from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class JudgeVerdict:
    passed: bool | None
    score: float | None
    rationale: str
    details: dict[str, Any]


class JudgeClient:
    """Pluggable LLM-as-judge adapter.

    For now this returns a skipped verdict until a judge model is wired in.
    """

    def __init__(self, enabled: bool = False, model: str | None = None):
        self.enabled = enabled
        self.model = model

    def evaluate(
        self,
        *,
        metric_name: str,
        rubric: str,
        case_input: str,
        trace: dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> JudgeVerdict:
        if not self.enabled:
            return JudgeVerdict(
                passed=None,
                score=None,
                rationale=(
                    "Judge model is not configured yet. Metric scaffold is ready "
                    "for later calibration."
                ),
                details={"metric_name": metric_name, "rubric": rubric},
            )
        raise NotImplementedError(
            "Wire your preferred judge model here once credentials are available."
        )

