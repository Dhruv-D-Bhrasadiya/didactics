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
```

The factory also supports `GROQ_API_KEY`, `GROQ_API_KEY_FALLBACK_1`, and `OPENAI_API_KEY`.

## Run the intent agent

From the repository root, with the virtual environment active:

```powershell
python -c "from backend.app.agents.intent_analyzer_agent import create_intent_analyzer_agent; agent = create_intent_analyzer_agent(provider='gemini'); print(agent.analyze('Teach me binary search in Python').model_dump_json(indent=2))"
```

The command makes one provider request and prints validated `IntentAnalysis` JSON.
