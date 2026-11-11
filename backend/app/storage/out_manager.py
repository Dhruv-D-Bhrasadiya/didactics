"""Filesystem boundary for workflow run directories and JSON artifacts."""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = REPOSITORY_ROOT / "out"
RUNS_DIR = OUT_DIR / "runs"
LOGS_DIR = OUT_DIR / "logs"

def json_default(value: Any):
    if hasattr(value, "model_dump"): return value.model_dump(mode="json")
    if hasattr(value, "isoformat"): return value.isoformat()
    return str(value)

def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=json_default) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path

def create_run_directory(run_id: str | None = None) -> tuple[str, Path]:
    identifier = run_id or uuid4().hex
    run_dir = RUNS_DIR / identifier
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    (run_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
    return identifier, run_dir

def write_run_manifest(run_dir: Path, result: dict) -> Path:
    manifest = {
        "run_id": result.get("run_id"),
        "status": result.get("status"),
        "completed_stages": result.get("completed_stages", []),
        "files": sorted(str(path.relative_to(run_dir)) for path in run_dir.rglob("*") if path.is_file()),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return write_json(run_dir / "manifest.json", manifest)
