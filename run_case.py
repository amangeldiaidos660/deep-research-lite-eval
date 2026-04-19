from __future__ import annotations

import argparse
from types import SimpleNamespace

from dotenv import load_dotenv

from eval_framework.cli import run_suite


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run a single evaluation case")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--cases", default="eval_cases")
    parser.add_argument("--output", default="eval_runs")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--retry-backoff-seconds", type=float, default=1.0)
    parser.add_argument("--agent-requests-per-minute", type=float, default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--judge-model", default=None)
    parser.add_argument("--judge-provider", default=None)
    parser.add_argument("--judge-base-url", default=None)
    parser.add_argument("--judge-requests-per-minute", type=float, default=None)
    parser.add_argument("--judge-max-retries", type=int, default=2)
    parser.add_argument("--judge-retry-backoff-seconds", type=float, default=2.0)
    parser.add_argument("--enable-judge", action="store_true")
    args = parser.parse_args()

    run_args = SimpleNamespace(
        cases=args.cases,
        case_ids=[args.case_id],
        output=args.output,
        repeats=args.repeats,
        concurrency=args.concurrency,
        max_retries=args.max_retries,
        retry_backoff_seconds=args.retry_backoff_seconds,
        agent_requests_per_minute=args.agent_requests_per_minute,
        model=args.model,
        judge_model=args.judge_model,
        judge_provider=args.judge_provider,
        judge_base_url=args.judge_base_url,
        judge_requests_per_minute=args.judge_requests_per_minute,
        judge_max_retries=args.judge_max_retries,
        judge_retry_backoff_seconds=args.judge_retry_backoff_seconds,
        enable_judge=args.enable_judge,
    )
    return run_suite(run_args)


if __name__ == "__main__":
    raise SystemExit(main())
