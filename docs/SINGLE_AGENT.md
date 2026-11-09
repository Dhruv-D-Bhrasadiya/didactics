# Legacy prototype — Request Understanding Agent

This document describes the prototype preserved in the current source tree. It is **not** the architecture for the focused LeetCode MVP. The new product flow and implementation requirements are documented in the root [README](../README.md), [SRS](SRS.md), and [diagram](../diagram.md).

The legacy Stage 1 uses one LLM agent and one structured response per request. It extracts the user's goal and topic, learner level, explanation depth, prior knowledge, objectives, constraints, deliverables, concept inventory and order, assumptions, and ambiguity/clarification needs. It does not generate lesson content.

The canonical model response is `RequestUnderstanding`, defined in `backend/app/schemas/intent.py`. `IntentAnalysis` remains an alias for callers of the old API; it is not a second schema.

## Run the legacy agent

Set credentials in `backend/.env`:

```env
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
DEFAULT_PROVIDER=gemini
```

From the repository root:

```powershell
.\\.venv\\Scripts\\python.exe main.py --provider groq --model "qwen/qwen3.8-27b" --query "Teach me binary search in Java"
.\\.venv\\Scripts\\python.exe main.py --provider gemini --model "gemini-3.6-flash" --query "Teach me binary search in Java"
```

Supported providers are `groq`, `gemini`, and `openai`. The selected run uses one explicit provider and model. Key rotation, when configured, stays within that provider. Successful and failed runs save diagnostic JSON under `debug/request_understanding_agent/`.

## Legacy tests

```powershell
.\\.venv\\Scripts\\python.exe -m unittest discover -s backend/test -p "test_*.py" -v
```

These tests use a fake LLM and do not require API credentials.
