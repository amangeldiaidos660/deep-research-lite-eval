# Deep Research Lite Eval Harness

Evaluation framework for the shipped `deep-research-lite` agent. The agent is
treated as a black box: this repository adds a test harness, metric plugins,
trace storage, run reports, and a local HTML viewer without replacing the
agent's implementation.

## Goal

This repository is the take-home submission scaffold for evaluating a
single-turn research agent against a local corpus. The framework is designed
around six dimensions:

- correctness
- groundedness / citation faithfulness
- tool use quality
- safety / refusal behavior
- efficiency
- reliability / flakiness

## Repo Layout

```text
.
├── agent.py                 # shipped agent under test
├── tools.py                 # shipped tool implementations
├── run.py                   # shipped one-shot CLI
├── eval_framework/          # evaluation runner, metrics, reporting, viewer
├── eval_cases/              # checked-in evaluation cases
├── README.agent.md          # original agent README preserved for reference
├── task.md                  # take-home assignment prompt
└── requirements.txt
```

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill `.env` with the model credentials you want to use for local runs.

## Main Commands

Run the suite:

```powershell
python run_eval.py run --cases eval_cases --output eval_runs --repeats 3
```

Re-score a cached run:

```powershell
python run_eval.py rescore --summary eval_runs\<run_id>\summary.json
```

Diff two runs:

```powershell
python run_eval.py diff --current eval_runs\<new>\summary.json --previous eval_runs\<old>\summary.json
```

## Current Status

- modular metric registry is in place
- hard assertions and reporting work end-to-end
- replay / rescore flow is wired
- HTML viewer is generated per run
- judge adapter is scaffolded and ready to connect to a real model
- starter case suite is checked in and can be expanded into the final suite

## Notes

- runtime artifacts are written under `eval_runs/` and are gitignored by
  default
- committed fixture traces for the final submission should live in a dedicated
  directory, separate from local development runs
- the original project description is preserved in `README.agent.md`
