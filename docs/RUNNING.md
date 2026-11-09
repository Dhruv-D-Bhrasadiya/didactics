# Running Didactics

## Prerequisites

- Windows PowerShell
- Python 3.10 or newer
- An API key for the provider you want to use

## Create and activate the virtual environment

Run these commands from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation for the current terminal, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

## Configure API keys

Create `backend/.env`:

```env
GEMINI_API_KEY=your_primary_key
GEMINI_API_KEY_FALLBACK_1=your_fallback_key
GROQ_API_KEY=your_groq_key
DEFAULT_PROVIDER=gemini
```

The factory also supports `GROQ_API_KEY`, `GROQ_API_KEY_FALLBACK_1`, and `OPENAI_API_KEY`.

## Run Stage 1

From the repository root, explicitly choose the provider and model you want to test:

```powershell
.\.venv\Scripts\python.exe main.py --provider groq --model "qwen/qwen3.8-27b" --query "Teach me binary search in Java"
.\.venv\Scripts\python.exe main.py --provider gemini --model "gemini-3.6-flash" --query "Teach me binary search in Java"
```

Each successful run makes one model invocation, prints the single-schema analysis, and saves the full run and trace to `debug/request_understanding_agent/`. Provider client retries are disabled. If a provider has multiple configured keys, eligible quota/auth/connection/server errors may retry with another key for the same model. Use `--help` for CLI options; see [SINGLE_AGENT.md](SINGLE_AGENT.md) for all schema, token, and model-selection details.
