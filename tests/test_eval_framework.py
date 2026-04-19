from __future__ import annotations

import unittest
from pathlib import Path

from eval_framework.case_loader import load_cases
from eval_framework.pricing import effective_cost_usd, normalize_model_name
from eval_framework.report import build_suite_summary
from eval_framework.schema import AttemptResult, CaseRunSummary, MetricResult
from eval_framework.viewer import render_viewer


class EvalFrameworkTests(unittest.TestCase):
    def test_eval_suite_contains_twelve_cases(self) -> None:
        cases = load_cases("eval_cases")
        self.assertEqual(len(cases), 12)
        self.assertTrue(any(case.id == "voyager_happy_path" for case in cases))
        self.assertTrue(any(case.id == "format_and_finish_compliance" for case in cases))

    def test_pricing_normalizes_versioned_model_names(self) -> None:
        trace = {
            "model": "claude-haiku-4-5-20251001",
            "cost_usd": 0.0,
            "total_tokens": {"input": 7000, "output": 622},
        }
        self.assertEqual(normalize_model_name(trace["model"]), "claude-haiku-4-5")
        self.assertGreater(effective_cost_usd(trace), 0)

    def test_summary_uses_effective_cost_when_trace_cost_is_zero(self) -> None:
        trace = {
            "model": "claude-haiku-4-5-20251001",
            "cost_usd": 0.0,
            "wall_time_ms": 1234,
            "total_tokens": {"input": 7000, "output": 622},
            "messages": [],
        }
        attempt = AttemptResult(
            case_id="demo_case",
            attempt_index=1,
            trace_path="demo_trace.json",
            trace=trace,
            metric_results=[MetricResult(name="hard_assertions", passed=True, score=1.0, reason="ok")],
        )
        summary = build_suite_summary(
            cases=[
                CaseRunSummary(
                    case_id="demo_case",
                    description="demo",
                    tags=[],
                    spec={"id": "demo_case", "input": "demo"},
                    attempts=[attempt],
                )
            ],
            repeats=1,
        )
        self.assertGreater(summary["aggregate"]["total_cost_usd"], 0)
        self.assertEqual(
            summary["cases"][0]["attempt_results"][0]["trace"]["model"],
            "claude-haiku-4-5-20251001",
        )

    def test_viewer_renders_message_timeline(self) -> None:
        trace = {
            "stopped_reason": "finish",
            "wall_time_ms": 123,
            "cost_usd": 0.0,
            "model": "claude-haiku-4-5-20251001",
            "total_tokens": {"input": 100, "output": 20},
            "messages": [
                {"role": "user", "content": "hello"},
                {
                    "role": "assistant",
                    "text": "searching",
                    "latency_ms": 10,
                    "tool_calls": [{"name": "web_search", "args": {"query": "hello"}}],
                },
                {
                    "role": "tool",
                    "name": "web_search",
                    "tool_use_id": "tool-1",
                    "latency_ms": 0,
                    "content": [{"url": "https://corpus.local/example"}],
                },
            ],
        }
        summary = {
            "aggregate": {
                "case_count": 1,
                "attempt_count": 1,
                "attempt_pass_rate": 1.0,
                "total_cost_usd": 0.0,
                "p50_latency_ms": 123,
                "p95_latency_ms": 123,
                "latency_stddev_ms": 0.0,
                "cost_stddev_usd": 0.0,
                "mean_tool_calls_per_attempt": 1.0,
                "tool_calls_stddev": 0.0,
            },
            "cases": [
                {
                    "case_id": "demo_case",
                    "description": "demo",
                    "pass_count": 1,
                    "attempts": 1,
                    "pass_pow_k": 1.0,
                    "reliability_k": 3,
                    "attempt_results": [
                        {
                            "attempt_index": 1,
                            "trace_path": "demo_trace.json",
                            "passed": True,
                            "trace": trace,
                            "metric_results": [],
                        }
                    ],
                }
            ],
        }
        output_dir = Path("tests_output")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "viewer.html"
        try:
            render_viewer(summary, output_path)
            rendered = output_path.read_text(encoding="utf-8")
        finally:
            if output_path.exists():
                output_path.unlink()
        self.assertIn("Message Timeline", rendered)
        self.assertIn("Tool Call 1: web_search", rendered)
        self.assertIn("tool_use_id: tool-1", rendered)


if __name__ == "__main__":
    unittest.main()
