# Running the archived prototype

The files in the current `backend/` and root `main.py` are preserved from the previous Didactics prototype. They are not yet the implementation of the focused LeetCode MVP described in the root README and SRS.

## Prototype prerequisites

- Windows PowerShell
- Python 3.10 or newer
- An API key for the provider being tested

Create and activate a virtual environment from the repository root:

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install -r backend/requirements.txt
```

Create `backend/.env` with the provider credentials required by the prototype:

```env
GEMINI_API_KEY=your_key
GROQ_API_KEY=your_key
OPENAI_API_KEY=your_key
DEFAULT_PROVIDER=gemini
```

Run the legacy request-understanding CLI:

```powershell
.\\.venv\\Scripts\\python.exe main.py --provider groq --model "qwen/qwen3.8-27b" --query "Teach me binary search in Java"
```

The prototype run writes debug artifacts under `debug/request_understanding_agent/`. Do not commit real API keys or debug records containing private prompts.

## Tests

```powershell
.\\.venv\\Scripts\\python.exe -m unittest discover -s backend/test -p "test_*.py" -v
```

For the focused MVP implementation plan, see the root [README](../README.md), [SRS](SRS.md), and [architecture diagram](../diagram.md).
