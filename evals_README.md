# Evaluation Framework Scaffold

This repository now includes a starter evaluation harness for `deep-research-lite`.

## What exists already

- `eval_framework/` contains the modular runner, scoring, storage, report, and HTML viewer scaffolding.
- `eval_cases/` contains starter JSON cases aligned to correctness, groundedness, tool use, safety, efficiency, and reliability goals.
- `eval_framework/judge.py` is intentionally left as a pluggable adapter so you can wire in the judge model after credentials are available.

## Example commands

```powershell
python -m eval_framework.cli run --cases eval_cases --output eval_runs --repeats 3
python -m eval_framework.cli rescore --summary eval_runs/<run_id>/summary.json
python -m eval_framework.cli diff --current eval_runs/<new>/summary.json --previous eval_runs/<old>/summary.json
```
