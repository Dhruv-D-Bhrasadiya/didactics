import argparse
import json
import sys
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from backend.app.agents.intent_analyzer_agent import create_request_understanding_agent
from backend.app.agents.run_artifacts import save_run_artifact
from backend.app.agents.utils import ModelResponseError
from backend.app.config import get_settings


def parse_args() -> argparse.Namespace:
    """Parse command-line options for one Stage 1 analysis.

    Args:
        None.

    Returns:
        argparse.Namespace: Provider, model, and learner query options.

    Example:
        args = parse_args()  # Reads options supplied to the current process.
    """
    parser = argparse.ArgumentParser(
        description="Run Didactics' single Stage 1 request-understanding agent."
    )
    parser.add_argument(
        "--provider",
        choices=("gemini", "groq", "openai"),
        help="LLM provider; defaults to DEFAULT_PROVIDER in backend/.env.",
    )
    parser.add_argument(
        "--model",
        help="Exact provider model ID (for example, qwen/qwen3-32b).",
    )
    parser.add_argument(
        "--query",
        default="Teach me binary search in Java.",
        help="Learner request to analyze.",
    )
    return parser.parse_args()


def main() -> int:
    """Run request understanding, save its artifact, and print the result.

    Args:
        None.

    Returns:
        int: Zero on success, or one when setup or analysis fails.

    Example:
        exit_code = main()
    """
    args = parse_args()
    run_id = uuid4().hex
    started_at = datetime.now(timezone.utc)
    started_clock = perf_counter()
    provider = args.provider or "unresolved"
    model_name = args.model.strip() if args.model else "unresolved"
    run_metadata = {
        "run_id": run_id,
        "provider": provider,
        "model_name": model_name,
        "started_at_utc": started_at.isoformat(),
        "request": args.query,
    }

    agent = None
    trace = None
    try:
        settings = get_settings()
        provider = (args.provider or settings.default_provider).strip().lower()
        configured_model = getattr(settings, f"{provider}_model", "")
        model_name = args.model.strip() if args.model else configured_model
        run_metadata["provider"] = provider
        run_metadata["model_name"] = model_name
        agent = create_request_understanding_agent(
            provider=provider,
            model_name=model_name,
            app_settings=settings,
        )
        analysis, trace = agent.analyze_with_trace(args.query)
        run_metadata["duration_ms"] = (perf_counter() - started_clock) * 1000
        run_metadata["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
        run_metadata["token_usage"] = trace.token_usage.model_dump(mode="json")
        artifact = {
            "run": run_metadata,
            "analysis": analysis.model_dump(mode="json"),
            "trace": trace.model_dump(mode="json"),
        }
    except Exception as exc:
        run_metadata["duration_ms"] = (perf_counter() - started_clock) * 1000
        run_metadata["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
        run_metadata["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        if isinstance(exc, ModelResponseError):
            trace = exc.trace
            run_metadata["token_usage"] = trace.token_usage.model_dump(mode="json")
        artifact = {
            "run": run_metadata,
            "trace": trace.model_dump(mode="json") if trace else None,
        }
        if agent:
            for key in agent.api_keys:
                run_metadata["error"]["message"] = run_metadata["error"][
                    "message"
                ].replace(key, "[REDACTED]")

        artifact_path = save_run_artifact(provider, model_name, artifact, run_id=run_id)
        print(f"Stage 1 failed; run details saved to: {artifact_path}", file=sys.stderr)
        print(f"{type(exc).__name__}: {run_metadata['error']['message']}", file=sys.stderr)
        return 1

    artifact_path = save_run_artifact(provider, model_name, artifact, run_id=run_id)
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    print(f"\nStage 1 run saved to: {artifact_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
