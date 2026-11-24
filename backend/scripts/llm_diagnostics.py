from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import TYPE_CHECKING

from pydantic import SecretStr

from backend.app.configs.config import get_settings

if TYPE_CHECKING:
    from google import genai
    from groq import Groq


def _secret_value(secret: SecretStr | None, setting_name: str) -> str:
    if secret is None:
        raise RuntimeError(f"Configure the {setting_name.upper()} environment variable.")
    return secret.get_secret_value()


def _groq_client() -> Groq:
    from groq import Groq

    settings = get_settings()
    return Groq(api_key=_secret_value(settings.groq_api_key, "groq_api_key"))


def _gemini_client() -> genai.Client:
    from google import genai

    settings = get_settings()
    return genai.Client(
        api_key=_secret_value(settings.gemini_api_key, "gemini_api_key")
    )


class CheckModel:
    @staticmethod
    def groq_model_check() -> None:
        models_list = _groq_client().models.list()
        print("--- Available Groq Models ---")
        for model in models_list.data:
            print(f"- {model.id}")

    @staticmethod
    def gemini_model_check() -> None:
        models_list = _gemini_client().models.list()
        print("--- Available Gemini Models ---")
        for model in models_list:
            print(f"- {model.name} (Supported actions: {model.supported_actions})")


class CheckUsage:
    @staticmethod
    def groq_rate_limits(model_name: str = "openai/gpt-oss-20b") -> None:
        response = _groq_client().chat.completions.with_raw_response.create(
            messages=[{"role": "user", "content": "ping"}],
            model=model_name,
        )
        headers = response.headers
        print("--- Groq Rate Limits & Usage Status ---")
        print(
            "- Remaining Requests today (RPD): "
            f"{headers.get('x-ratelimit-remaining-requests')}"
        )
        print(
            "- Remaining Tokens this minute (TPM): "
            f"{headers.get('x-ratelimit-remaining-tokens')}"
        )
        print(
            "- Total Limit Requests per day: "
            f"{headers.get('x-ratelimit-limit-requests')}"
        )
        print(
            "- Total Limit Tokens per minute: "
            f"{headers.get('x-ratelimit-limit-tokens')}"
        )
        print(
            "- Limit Reset Time (Tokens): "
            f"{headers.get('x-ratelimit-reset-tokens')}"
        )

    @staticmethod
    def gemini_context_limits(model_name: str = "gemini-3.8-flash") -> None:
        model_info = _gemini_client().models.get(model=model_name)
        print(f"--- Gemini Limits for {model_name} ---")
        print(f"- Input Token Limit: {model_info.input_token_limit}")
        print(f"- Output Token Limit: {model_info.output_token_limit}")

    @staticmethod
    def gemini_count_tokens(
        text_prompt: str = "How many credits does this sentence take?",
        model_name: str = "gemini-3.8-flash",
    ) -> None:
        response = _gemini_client().models.count_tokens(
            model=model_name,
            contents=text_prompt,
        )
        print("--- Gemini Pre-flight Token Count ---")
        print(f"- Prompt: {text_prompt!r}")
        print(f"- Total Tokens Required: {response.total_tokens}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect configured LLM providers.")
    parser.add_argument(
        "provider",
        choices=("groq", "gemini"),
        help="Provider to inspect.",
    )
    parser.add_argument(
        "action",
        choices=("models", "limits", "count-tokens"),
        help="Diagnostic to run.",
    )
    parser.add_argument("--model", help="Optional provider model ID.")
    parser.add_argument(
        "--prompt",
        default="How many credits does this sentence take?",
        help="Text to count with Gemini.",
    )
    args = parser.parse_args(argv)

    if args.action == "models":
        if args.provider == "groq":
            CheckModel.groq_model_check()
        else:
            CheckModel.gemini_model_check()
    elif args.action == "limits":
        if args.provider == "groq":
            CheckUsage.groq_rate_limits(args.model or "openai/gpt-oss-20b")
        elif args.model:
            CheckUsage.gemini_context_limits(args.model)
        else:
            CheckUsage.gemini_context_limits()
    elif args.provider == "gemini":
        CheckUsage.gemini_count_tokens(
            text_prompt=args.prompt,
            model_name=args.model or "gemini-3.8-flash",
        )
    else:
        parser.error("count-tokens is supported only for Gemini.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
