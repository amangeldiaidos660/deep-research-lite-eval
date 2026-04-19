from __future__ import annotations

import json
import os
import re
from dataclasses import asdict
from dataclasses import dataclass
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request


@dataclass
class JudgeVerdict:
    passed: bool | None
    score: float | None
    rationale: str
    details: dict[str, Any]


class JudgeClient:
    """Pluggable LLM-as-judge adapter.

    Supports Anthropic directly and OpenAI-compatible chat-completions APIs.
    """

    def __init__(
        self,
        enabled: bool = False,
        model: str | None = None,
        provider: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        self.enabled = enabled
        self.model = model or os.getenv("JUDGE_MODEL")
        self.provider = (provider or os.getenv("JUDGE_PROVIDER") or "anthropic").lower()
        self.api_key = api_key or os.getenv("JUDGE_API_KEY")
        if not self.api_key and self.provider == "anthropic":
            self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.base_url = base_url or os.getenv("JUDGE_BASE_URL")

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
        if not self.model:
            return JudgeVerdict(
                passed=None,
                score=None,
                rationale="Judge is enabled but no judge model is configured.",
                details={"metric_name": metric_name, "rubric": rubric},
            )
        if not self.api_key:
            return JudgeVerdict(
                passed=None,
                score=None,
                rationale="Judge is enabled but no judge API key is configured.",
                details={"metric_name": metric_name, "rubric": rubric},
            )

        prompt = self._build_prompt(
            metric_name=metric_name,
            rubric=rubric,
            case_input=case_input,
            trace=trace,
            params=params or {},
        )
        try:
            raw = self._call_model(prompt)
            verdict = self._parse_verdict(raw)
            verdict.details.update(
                {
                    "metric_name": metric_name,
                    "rubric": rubric,
                    "judge_provider": self.provider,
                    "judge_model": self.model,
                }
            )
            return verdict
        except Exception as exc:
            return JudgeVerdict(
                passed=None,
                score=None,
                rationale=f"Judge invocation failed: {type(exc).__name__}: {exc}",
                details={
                    "metric_name": metric_name,
                    "rubric": rubric,
                    "judge_provider": self.provider,
                    "judge_model": self.model,
                },
            )

    def _build_prompt(
        self,
        *,
        metric_name: str,
        rubric: str,
        case_input: str,
        trace: dict[str, Any],
        params: dict[str, Any],
    ) -> str:
        compact_trace = {
            "question": trace.get("question"),
            "final_answer": trace.get("final_answer"),
            "citations": trace.get("citations", []),
            "stopped_reason": trace.get("stopped_reason"),
            "error": trace.get("error"),
            "messages": trace.get("messages", []),
            "supporting_texts": trace.get("fetched_supporting_texts", {}),
            "params": params,
        }
        return (
            "You are an evaluation judge for an AI research agent.\n"
            "Apply the rubric strictly. Return only valid JSON with keys "
            '"passed", "score", "rationale", and "evidence".\n'
            "- passed: boolean\n"
            "- score: number from 0.0 to 1.0\n"
            "- rationale: short string\n"
            "- evidence: list of short strings\n\n"
            f"Metric: {metric_name}\n"
            f"Rubric: {rubric}\n"
            f"User question: {case_input}\n\n"
            "Trace payload:\n"
            f"{json.dumps(compact_trace, ensure_ascii=False)}"
        )

    def _call_model(self, prompt: str) -> str:
        if self.provider == "anthropic":
            from anthropic import Anthropic

            client = Anthropic(api_key=self.api_key)
            response = client.messages.create(
                model=self.model,
                max_tokens=600,
                temperature=0.0,
                system=(
                    "You are a strict evaluator. Return only JSON with keys "
                    "passed, score, rationale, evidence."
                ),
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(
                block.text for block in response.content if getattr(block, "type", "") == "text"
            )

        if self.provider in {"openai", "openai_compatible"}:
            base_url = (self.base_url or "https://api.openai.com/v1").rstrip("/")
            payload = {
                "model": self.model,
                "temperature": 0.0,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a strict evaluator. Return only JSON with keys "
                            "passed, score, rationale, evidence."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            }
            request_obj = urllib_request.Request(
                url=f"{base_url}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                method="POST",
            )
            try:
                with urllib_request.urlopen(request_obj, timeout=90) as response:
                    raw = json.loads(response.read().decode("utf-8"))
            except urllib_error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
            message = raw["choices"][0]["message"]["content"]
            if isinstance(message, list):
                return "".join(
                    item.get("text", "") for item in message if isinstance(item, dict)
                )
            return str(message)

        raise ValueError(f"Unsupported judge provider: {self.provider}")

    def _parse_verdict(self, raw: str) -> JudgeVerdict:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", cleaned)
            cleaned = re.sub(r"\n```$", "", cleaned)
        payload = json.loads(cleaned)
        return JudgeVerdict(
            passed=bool(payload.get("passed")),
            score=float(payload.get("score", 0.0)),
            rationale=str(payload.get("rationale", "")),
            details={"evidence": payload.get("evidence", []), "raw_verdict": payload},
        )
