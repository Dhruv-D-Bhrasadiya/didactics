# Using One Agent

The current standalone agent is `IntentAnalyzerAgent`. It accepts one learner query and returns a validated `IntentAnalysis` model.

## Real provider input

Configure `backend/.env`, activate `.venv`, and run from the repository root:

```powershell
python -c "from backend.app.agents.intent_analyzer_agent import create_intent_analyzer_agent; query = 'Explain recursion to a beginner with a Python example'; agent = create_intent_analyzer_agent(provider='gemini'); result = agent.analyze(query); print(result.model_dump_json(indent=2))"
```

Change `query` to the learner request you want to analyze. Supported providers are `gemini`, `groq`, and `openai` when their API keys and dependencies are installed.

## No-network input example

Use a fake LLM to inspect the agent flow without an API request:

```powershell
python -c "from types import SimpleNamespace; from backend.app.agents.intent_analyzer_agent import IntentAnalyzerAgent; response = '{\"domain\": \"computer science\", \"topic\": \"binary search\"}'; fake_llm = SimpleNamespace(invoke=lambda messages: SimpleNamespace(content=response)); agent = IntentAnalyzerAgent('test-model', ['test-key'], lambda *_: fake_llm); print(agent.analyze('Teach me binary search').model_dump_json(indent=2))"
```

The returned object can also be used as a dictionary:

```python
result.model_dump()
```
