# Stage 1 — Single Request-Understanding Agent

Stage 1 now uses one LLM agent and one structured response per successful request. It extracts the user's goal and topic, learner level, explanation depth, prior knowledge, objectives, constraints, deliverables, concept inventory and order, assumptions, and ambiguity/clarification needs. It does not create lesson content or run any later stage.

The canonical model response is `RequestUnderstanding`, defined in `backend/app/schemas/intent.py`. `IntentAnalysis` remains an alias for callers of the old API; it is not a second schema.

## Run Stage 1

Set the provider key in `backend/.env`:

```env
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
DEFAULT_PROVIDER=gemini
```

From the repository root, run one provider/model at a time:

```powershell
.\.venv\Scripts\python.exe main.py --provider groq --model "qwen/qwen3.8-27b" --query "Teach me binary search in Java"
.\.venv\Scripts\python.exe main.py --provider gemini --model "gemini-3.6-flash" --query "Teach me binary search in Java"
```

Use the exact model ID supported by the selected provider/account. `--model` overrides the provider's `GROQ_MODEL` or `GEMINI_MODEL` setting for this run. If omitted, the configured model is used. `--provider` can be omitted to use `DEFAULT_PROVIDER`. Each invocation selects only the requested provider and model; it does not silently fall back to another provider or model, so comparisons remain meaningful. Provider client retries are disabled. If multiple keys are configured for that same provider, eligible quota/auth/connection/server errors can retry the same model with its next key. The trace's `attempt_count` reports these agent-level attempts.

Run `.\.venv\Scripts\python.exe main.py --help` to see the CLI options. The default query is `Teach me binary search in Java.`

## Output and debug records

The command prints the structured result and saves a JSON record under `debug/request_understanding_agent/`. Each filename contains a UTC timestamp, provider, and sanitized model ID. The record includes:

- The original request, selected provider/model, UTC start/completion times, and elapsed time.
- The complete validated `analysis`.
- The trace with exact system/user messages, raw model response, parsed JSON, token usage when returned by the provider, duration, and attempt count.

Provider usage fields differ. Missing token counts are `null`; this agent does not estimate pre-call tokens. `provider_usage` retains usage data returned by LangChain. `confidence` is the model's estimate, not a calibrated probability. A failed parse saves its raw response and prompt in the error artifact; provider/configuration failures also save an error record before the command exits nonzero. API keys are never included in the run record.

Debug files contain learner requests and full prompts; treat them as sensitive. Decision summaries and assumptions describe observable input/output, not hidden chain-of-thought.

## Model selection and configuration

Supported providers are `groq`, `gemini`, and `openai`. Select a model with `--model` or configure `GROQ_MODEL`, `GEMINI_MODEL`, or `OPENAI_MODEL` in `backend/.env`. The credential settings are `GROQ_API_KEY`, optional `GROQ_API_KEY_FALLBACK_1`, `GEMINI_API_KEY`, optional `GEMINI_API_KEY_FALLBACK_1`, and `OPENAI_API_KEY`. The chosen provider must have at least one configured key.

Changing the provider/model for a comparison is an explicit CLI/configuration choice. Key rotation stays within the chosen provider and model. The recorded trace confirms which provider/model the agent used.

## Tests

The unit tests use a fake LLM and do not send API requests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend\test -p "test_*.py" -v
```
