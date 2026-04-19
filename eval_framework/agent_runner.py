from __future__ import annotations

import traceback
from pathlib import Path
from typing import Any


class AgentRunner:
    """Thin wrapper around the shipped agent.

    The framework treats the agent as a black box and records startup failures
    as error traces rather than crashing the whole suite.
    """

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root)

    def run(self, question: str, model: str | None = None) -> dict[str, Any]:
        try:
            from agent import run_agent

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

