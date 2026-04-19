from __future__ import annotations

import time
import traceback
from importlib import import_module
from pathlib import Path
from threading import Lock
from typing import Any


class AgentRunner:
    """Thin wrapper around the shipped agent.

    The framework treats the agent as a black box and records startup failures
    as error traces rather than crashing the whole suite.
    """

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root)
        self._import_lock = Lock()
        self._run_agent = None
        self._import_error: Exception | None = None

    def run(
        self,
        question: str,
        model: str | None = None,
        *,
        max_retries: int = 0,
        retry_backoff_seconds: float = 1.0,
    ) -> dict[str, Any]:
        retry_reasons: list[str] = []
        total_attempts = max_retries + 1
        for attempt_number in range(1, total_attempts + 1):
            trace = self._run_once(question, model=model)
            error_text = str(trace.get("error") or "")
            is_transient = self._is_transient_error(error_text)
            trace["runner_attempt_number"] = attempt_number
            trace["runner_total_attempts"] = total_attempts
            trace["runner_retry_reasons"] = retry_reasons[:]
            if not is_transient or attempt_number >= total_attempts:
                return trace
            retry_reasons.append(error_text)
            time.sleep(max(retry_backoff_seconds, 0.0) * attempt_number)
        return self._run_once(question, model=model)

    def _run_once(self, question: str, model: str | None = None) -> dict[str, Any]:
        try:
            run_agent = self._load_run_agent()
            result = run_agent(question, model=model) if model else run_agent(question)
            if hasattr(result, "to_dict"):
                return result.to_dict()
            return dict(result)
        except Exception as exc:
            return {
                "run_id": "startup-error",
                "question": question,
                "model": model or "",
                "messages": [],
                "final_answer": None,
                "citations": [],
                "stopped_reason": "error",
                "total_tokens": {"input": 0, "output": 0},
                "cost_usd": 0.0,
                "wall_time_ms": 0,
                "error": f"{type(exc).__name__}: {exc}",
                "startup_traceback": traceback.format_exc(),
            }

    def _load_run_agent(self):
        if self._run_agent is not None:
            return self._run_agent
        if self._import_error is not None:
            raise self._import_error

        with self._import_lock:
            if self._run_agent is not None:
                return self._run_agent
            if self._import_error is not None:
                raise self._import_error
            try:
                module = import_module("agent")
                self._run_agent = getattr(module, "run_agent")
                return self._run_agent
            except Exception as exc:
                self._import_error = exc
                raise

    @staticmethod
    def _is_transient_error(error_text: str) -> bool:
        lowered = error_text.lower()
        transient_markers = (
            "429",
            "500",
            "502",
            "503",
            "504",
            "rate limit",
            "timeout",
            "timed out",
            "connection reset",
            "connection aborted",
            "connection refused",
            "temporary failure",
            "temporarily unavailable",
            "service unavailable",
            "overloaded",
            "apiconnection",
            "network",
        )
        return any(marker in lowered for marker in transient_markers)
