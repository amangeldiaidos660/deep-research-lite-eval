from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

from eval_framework.agent_runner import AgentRunner
from eval_framework.case_loader import load_cases
from eval_framework.judge import JudgeClient
from eval_framework.metrics import build_registry
from eval_framework.report import build_diff, build_suite_summary, render_markdown
from eval_framework.schema import AttemptResult, CaseRunSummary
from eval_framework.storage import new_run_dir, read_json, write_json
from eval_framework.viewer import render_viewer


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Deep Research Lite eval harness")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Run the eval suite against the shipped agent")
    run_cmd.add_argument("--cases", default="eval_cases")
    run_cmd.add_argument("--output", default="eval_runs")
    run_cmd.add_argument("--repeats", type=int, default=1)
    run_cmd.add_argument("--concurrency", type=int, default=1)
    run_cmd.add_argument("--max-retries", type=int, default=2)
    run_cmd.add_argument("--retry-backoff-seconds", type=float, default=1.0)
    run_cmd.add_argument("--model", default=None)
    run_cmd.add_argument("--judge-model", default=None)
    run_cmd.add_argument("--judge-provider", default=None)
    run_cmd.add_argument("--judge-base-url", default=None)
    run_cmd.add_argument("--enable-judge", action="store_true")

    rescore_cmd = sub.add_parser("rescore", help="Re-score a saved run without calling the agent")
    rescore_cmd.add_argument("--summary", required=True)
    rescore_cmd.add_argument("--judge-model", default=None)
    rescore_cmd.add_argument("--judge-provider", default=None)
    rescore_cmd.add_argument("--judge-base-url", default=None)
    rescore_cmd.add_argument("--enable-judge", action="store_true")

    diff_cmd = sub.add_parser("diff", help="Diff two summary files")
    diff_cmd.add_argument("--current", required=True)
    diff_cmd.add_argument("--previous", required=True)

    args = parser.parse_args()
    if args.command == "run":
        return run_suite(args)
    if args.command == "rescore":
        return rescore_suite(args)
    if args.command == "diff":
        return diff_summaries(args)
    return 1


def run_suite(args: argparse.Namespace) -> int:
    cases = load_cases(args.cases)
    run_dir = new_run_dir(args.output)
    runner = AgentRunner(Path.cwd())
    registry = build_registry()
    judge = JudgeClient(
        enabled=args.enable_judge,
        model=args.judge_model,
        provider=args.judge_provider,
        base_url=args.judge_base_url,
    )
    attempts_by_case: dict[str, list[AttemptResult]] = defaultdict(list)
    case_by_id = {case.id: case for case in cases}

    work_items = [
        (case, attempt_index)
        for case in cases
        for attempt_index in range(1, args.repeats + 1)
    ]
    max_workers = max(1, min(args.concurrency, len(work_items) or 1))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _run_attempt,
                case=case,
                attempt_index=attempt_index,
                run_dir=run_dir,
                runner=runner,
                registry=registry,
                judge=judge,
                model=args.model,
                max_retries=args.max_retries,
                retry_backoff_seconds=args.retry_backoff_seconds,
            ): (case.id, attempt_index)
            for case, attempt_index in work_items
        }
        for future in as_completed(futures):
            attempt = future.result()
            attempts_by_case[attempt.case_id].append(attempt)

    case_summaries: list[CaseRunSummary] = []
    for case in cases:
        attempts = sorted(
            attempts_by_case.get(case.id, []),
            key=lambda item: item.attempt_index,
        )
        case_summaries.append(
            CaseRunSummary(
                case_id=case.id,
                description=case.description,
                tags=case.tags,
                spec=case.to_dict(),
                attempts=attempts,
            )
        )

    summary = build_suite_summary(cases=case_summaries, repeats=args.repeats)
    for case in summary["cases"]:
        case["reliability_k"] = summary["reliability_k"]
    write_json(run_dir / "summary.json", summary)
    render_markdown(summary, run_dir / "summary.md")
    render_viewer(summary, run_dir / "viewer.html")
    print(f"Run completed. Artifacts written to {run_dir}")
    return 0


def rescore_suite(args: argparse.Namespace) -> int:
    summary_path = Path(args.summary)
    summary = read_json(summary_path)
    judge = JudgeClient(
        enabled=args.enable_judge,
        model=args.judge_model,
        provider=args.judge_provider,
        base_url=args.judge_base_url,
    )
    registry = build_registry()

    refreshed_cases = []
    for case in summary.get("cases", []):
        attempts = []
        for attempt in case.get("attempt_results", []):
            trace = read_json(attempt["trace_path"])
            case_stub = _case_stub_from_case_payload(case, trace)
            metric_results = []
            metric_results.append(registry.get("hard_assertions").evaluate(case=case_stub, trace=trace, judge=judge))
            for metric_name in ("correctness", "groundedness", "tool_use", "safety", "efficiency"):
                metric_results.append(registry.get(metric_name).evaluate(case=case_stub, trace=trace, judge=judge))
            attempts.append(
                {
                    **attempt,
                    "metric_results": [item.to_dict() for item in metric_results],
                    "passed": all(item.passed for item in metric_results if item.passed is not None),
                }
            )
        refreshed_cases.append(
            {
                "case_id": case["case_id"],
                "description": case.get("description", ""),
                "tags": case.get("tags", []),
                "spec": case.get("spec", {}),
                "pass_count": sum(1 for attempt in attempts if attempt["passed"]),
                "attempts": len(attempts),
                "pass_rate": round(sum(1 for attempt in attempts if attempt["passed"]) / len(attempts), 4) if attempts else 0.0,
                "pass_pow_k": case.get("pass_pow_k", 0.0),
                "attempt_results": attempts,
                "reliability_k": summary.get("reliability_k", 3),
            }
        )

    rescored = {
        **summary,
        "cases": refreshed_cases,
    }
    out_path = summary_path.with_name(summary_path.stem + ".rescored.json")
    write_json(out_path, rescored)
    print(f"Rescored summary written to {out_path}")
    return 0


def diff_summaries(args: argparse.Namespace) -> int:
    current = read_json(args.current)
    previous = read_json(args.previous)
    diff = build_diff(current, previous)
    print(diff)
    return 0


def _run_attempt(
    *,
    case,
    attempt_index: int,
    run_dir: Path,
    runner: AgentRunner,
    registry,
    judge: JudgeClient,
    model: str | None,
    max_retries: int,
    retry_backoff_seconds: float,
) -> AttemptResult:
    trace = runner.run(
        case.input,
        model=model,
        max_retries=max_retries,
        retry_backoff_seconds=retry_backoff_seconds,
    )
    trace_path = run_dir / "traces" / f"{case.id}__attempt_{attempt_index}.json"
    write_json(trace_path, trace)

    metric_results = [
        registry.get("hard_assertions").evaluate(case=case, trace=trace, judge=judge)
    ]
    for metric_name in ("correctness", "groundedness", "tool_use", "safety", "efficiency"):
        metric_results.append(
            registry.get(metric_name).evaluate(case=case, trace=trace, judge=judge)
        )

    return AttemptResult(
        case_id=case.id,
        attempt_index=attempt_index,
        trace_path=str(trace_path),
        trace=trace,
        metric_results=metric_results,
    )


def _case_stub_from_case_payload(case_payload: dict, trace: dict):
    from eval_framework.schema import CaseSpec

    spec = dict(case_payload.get("spec", {}))
    if spec:
        return CaseSpec.from_dict(spec)
    return CaseSpec(
        id=str(case_payload["case_id"]),
        input=str(trace.get("question", "")),
        description=str(case_payload.get("description", "")),
        tags=[str(tag) for tag in case_payload.get("tags", [])],
        hard_assertions=[],
        soft_assertions=[],
    )


if __name__ == "__main__":
    raise SystemExit(main())
