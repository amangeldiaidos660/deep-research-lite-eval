from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from eval_framework.schema import CaseSpec


def _load_yaml(path: Path) -> dict:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            f"YAML case support requires PyYAML. Could not load {path.name}."
        ) from exc
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_cases(case_dir: str | Path) -> list[CaseSpec]:
    base = Path(case_dir)
    if not base.exists():
        raise FileNotFoundError(f"Case directory does not exist: {base}")

    specs: list[CaseSpec] = []
    for path in sorted(_iter_case_files(base)):
        if path.suffix.lower() == ".json":
            raw = json.loads(path.read_text(encoding="utf-8"))
        else:
            raw = _load_yaml(path)
        specs.append(CaseSpec.from_dict(raw))
    return specs


def _iter_case_files(base: Path) -> Iterable[Path]:
    for suffix in ("*.json", "*.yaml", "*.yml"):
        yield from base.rglob(suffix)

