import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def _safe_filename_part(value: str) -> str:
    """Normalize a label for safe use as one filename component.

    Args:
        value: Provider or model label to sanitize.

    Returns:
        str: Bounded filename-safe label, or ``"unspecified"`` if empty.

    Example:
        _safe_filename_part("models/example:v1")  # "models_example_v1"
    """
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return (safe.strip("._-") or "unspecified")[:80]


def save_run_artifact(
    provider: str,
    model_name: str,
    data: dict[str, Any],
    debug_dir: Path | None = None,
    run_id: str | None = None,
) -> Path:
    """Write a timestamped JSON record for one agent execution.

    Args:
        provider: Provider label used in the filename.
        model_name: Model label used in the filename.
        data: JSON-serializable run, analysis, or trace data.
        debug_dir: Output directory; defaults to the repository debug folder.
        run_id: Optional run identifier; generated when omitted.

    Returns:
        Path: Location of the saved JSON artifact.

    Example:
        path = save_run_artifact("groq", "qwen/model", {"run": {}})
    """
    timestamp = datetime.now(timezone.utc)
    run_id = run_id or uuid4().hex
    if debug_dir is None:
        repository_root = Path(__file__).resolve().parents[3]
        debug_dir = repository_root / "debug" / "request_understanding_agent"

    debug_dir.mkdir(parents=True, exist_ok=True)
    filename = (
        f"{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}_"
        f"{_safe_filename_part(provider)}_{_safe_filename_part(model_name)}_"
        f"{run_id[:8]}.json"
    )
    output_path = debug_dir / filename
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path
