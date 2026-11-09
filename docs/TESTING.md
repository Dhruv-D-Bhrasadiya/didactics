# Testing Didactics

Run tests from the repository root with the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m unittest backend.test.test_intent_analyzer_agent -v
```

The intent-agent tests use a fake LLM, so they do not make API requests or require a configured API key.

Compile the backend package and check imports:

```powershell
.\.venv\Scripts\python.exe -m compileall -q backend
.\.venv\Scripts\python.exe -c "from backend.app.agents.intent_analyzer_agent import RequestUnderstandingAgent; from backend.app.schemas import RequestUnderstanding; print('imports ok')"
```

Run the full discovered test suite:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend/test -p "test_*.py" -v
```
