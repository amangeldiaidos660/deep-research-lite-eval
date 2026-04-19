# Deep Research Lite Eval Harness

Evaluation framework for the shipped `deep-research-lite` agent. The agent is
treated as a black box: this repository wraps it with a reusable evaluation
harness, trace persistence, metric plugins, flaky-run reporting, diffing, and
a local HTML viewer.

## What This Repository Builds

The framework evaluates the agent across six dimensions:

- correctness
- groundedness / citation faithfulness
- tool use quality
- safety / refusal behavior
- efficiency
- reliability / flakiness

The harness is designed around the take-home requirements:

- JSON/YAML case loading
- hard assertions plus LLM-as-judge soft assertions
- retries for transient failures
- configurable concurrency
- trace replay and re-scoring without re-calling the agent
- run-level reporting and diffing
- local HTML inspection of failures

## Repository Layout

```text
.
├── agent.py                      # shipped agent under test
├── tools.py                      # shipped tool implementations
├── run.py                        # shipped CLI for the agent itself
├── run_eval.py                   # eval framework entrypoint
├── eval_framework/
│   ├── cli.py                    # run / rescore / diff commands
│   ├── agent_runner.py           # runner wrapper with retry handling
│   ├── judge.py                  # Anthropic + OpenAI-compatible judge adapter
│   ├── report.py                 # aggregate reporting and diffing
│   ├── viewer.py                 # local HTML report
│   └── metrics/                  # plugin-style metric implementations
├── eval_cases/                   # checked-in evaluation suite
├── README.agent.md               # original shipped README preserved
└── task.md                       # take-home prompt
```

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill `.env` with the credentials you want to use for the real run.

Minimum agent configuration:

```env
ANTHROPIC_API_KEY=...
DRL_MODEL=claude-haiku-4-5
DRL_SMALL_MODEL=claude-haiku-4-5
```

Optional judge configuration:

```env
JUDGE_PROVIDER=anthropic
JUDGE_MODEL=...
JUDGE_API_KEY=...
JUDGE_BASE_URL=
```

`JUDGE_PROVIDER` supports:

- `anthropic`
- `openai`
- `openai_compatible`

For OpenAI-compatible judge endpoints, set `JUDGE_BASE_URL`.

## Commands

Run the full suite:

```powershell
python run_eval.py run --cases eval_cases --output eval_runs --repeats 3 --concurrency 4 --max-retries 2 --retry-backoff-seconds 1.5
```

Run a smaller local smoke pass:

```powershell
python run_eval.py run --cases eval_cases --output eval_runs --repeats 1
```

Enable judge scoring:

```powershell
python run_eval.py run --cases eval_cases --output eval_runs --repeats 3 --enable-judge --judge-model <model_name>
```

Re-score an existing run without calling the agent again:

```powershell
python run_eval.py rescore --summary eval_runs\<run_id>\summary.json --enable-judge --judge-model <model_name>
```

Diff two runs:

```powershell
python run_eval.py diff --current eval_runs\<new>\summary.json --previous eval_runs\<old>\summary.json
```

## Current Evaluation Suite

The checked-in suite currently covers:

- multiple happy paths
- ambiguity disclosure
- refusal and confidentiality handling
- required tool-sequence behavior
- adversarial prompt-injection pressure
- source-quality conflicts
- out-of-corpus abstention
- finish / format compliance
- grounded citation checks

The suite is stored as independent case files so new metrics and new cases can
be added without editing runner core logic.

## Judge Design

`eval_framework/judge.py` provides a real adapter layer rather than a stub.

- Anthropic judge calls are supported directly via the Anthropic SDK.
- OpenAI-compatible judge calls are supported over `/chat/completions`.
- The judge is rubric-driven per metric / per case.
- Judge output is required to be structured JSON containing:
  - `passed`
  - `score`
  - `rationale`
  - `evidence`

Soft assertions remain skippable when judge credentials are not configured,
which keeps local infrastructure smoke tests cheap.

## Reporting

Each run produces:

- `summary.json`
- `summary.md`
- `viewer.html`
- `traces/*.json`

The aggregate report includes:

- attempt pass rate
- total cost
- p50 / p95 latency
- tool-call averages
- standard deviation for latency, cost, and tool counts
- per-case `pass^k` style reliability summary

Diff output surfaces:

- regressions
- improvements
- aggregate pass-rate delta
- cost delta
- latency delta
- added / removed cases

## Notes

- Local development run artifacts under `eval_runs/` are gitignored.
- Final fixture traces for submission should be committed separately from ad hoc
  development runs.
- The original shipped project description is preserved in `README.agent.md`.
