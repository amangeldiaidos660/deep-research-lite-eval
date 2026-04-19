from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def new_run_dir(output_root: str | Path) -> Path:
    root = Path(output_root)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = root / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "traces").mkdir(exist_ok=True)
    return run_dir


def write_json(path: str | Path, payload: dict | list) -> None:
    Path(path).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def read_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))

