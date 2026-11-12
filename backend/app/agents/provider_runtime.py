import json
import logging
import re
from typing import TypeVar, Type
from pydantic import BaseModel
from backend.app.config import get_settings
from backend.app.agents.utils import build_gemini_llm, build_groq_llm, secret_value

log = logging.getLogger("didactics.agents")
T = TypeVar("T", bound=BaseModel)

def _json_payload(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Model response did not contain a JSON object")
        value = json.loads(text[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError("Model response must be a JSON object")
    return value

def _normalize_schema_payload(payload: dict | list, schema: Type[T]) -> dict:
    """Normalize common model JSON shapes before strict Pydantic validation."""
    if schema.__name__ == "SolutionPortfolio":
        if isinstance(payload, list):
            if not payload or not isinstance(payload[0], dict) or "variant_id" not in payload[0]:
                raise ValueError("Agent 1 returned an empty or invalid list of solution approaches")
            payload = {
                "problem_summary": "Solution approaches generated from the supplied problem statement.",
                "approaches": payload,
                "recommended_variant_id": payload[0]["variant_id"],
                "comparison": [],
            }
            log.warning("Normalized Agent 1 root-level solution list into SolutionPortfolio")
        elif isinstance(payload, dict):
            if "approaches" not in payload:
                for alias in ("solutions", "variants", "solution_approaches"):
                    if isinstance(payload.get(alias), list):
                        payload["approaches"] = payload.pop(alias)
                        break
            if "recommended_variant_id" not in payload and payload.get("approaches"):
                first = payload["approaches"][0]
                if isinstance(first, dict) and first.get("variant_id"):
                    payload["recommended_variant_id"] = first["variant_id"]
            payload.setdefault("problem_summary", "Solution approaches generated from the supplied problem statement.")
            payload.setdefault("comparison", [])
    if not isinstance(payload, dict):
        raise ValueError(f"Model response for {schema.__name__} must be a JSON object")
    return payload


def invoke_structured(agent_name: str, system_prompt: str, user_prompt: str, schema: Type[T]) -> tuple[T, dict]:
    settings = get_settings()
    providers = [
        ("gemini", settings.gemini_model, [settings.gemini_api_key, settings.gemini_api_key_fallback_1], build_gemini_llm),
        ("groq", settings.groq_model, [settings.groq_api_key, settings.groq_api_key_fallback_1], build_groq_llm),
    ]
    failures = []
    for provider, model, secret_keys, builder in providers:
        keys = [secret_value(key) for key in secret_keys if secret_value(key)]
        for key_index, api_key in enumerate(keys):
            try:
                llm = builder(api_key, model)
                response = llm.invoke([("system", system_prompt), ("user", user_prompt)])
                raw = getattr(response, "content", response)
                if isinstance(raw, list):
                    raw = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in raw)
                parsed = schema.model_validate(_normalize_schema_payload(_json_payload(str(raw)), schema))
                trace = {"agent": agent_name, "provider": provider, "model": model, "key_index": key_index, "usage": getattr(response, "usage_metadata", None) or {}, "status": "success"}
                log.info("%s completed using %s/%s", agent_name, provider, model)
                return parsed, trace
            except Exception as exc:
                message = f"{provider}/{model} key#{key_index + 1}: {type(exc).__name__}: {exc}"
                failures.append(message)
                log.exception("%s provider attempt failed: %s", agent_name, message)
                continue
    raise RuntimeError(f"{agent_name} failed on Gemini and Groq. " + " | ".join(failures[-6:]))
