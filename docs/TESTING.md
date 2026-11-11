# Testing Didactics

The focused MVP test strategy is defined here. The currently present tests exercise the archived request-understanding prototype; they do not yet test LeetCode lookup or either new learning path.

## Required MVP test layers

### 1. Problem lookup
- Valid problem number maps to the expected normalized problem fixture.
- Blank, malformed, zero, and negative IDs are rejected before network access.
- Not-found, upstream timeout, rate limit, malformed payload, and missing optional metadata are handled distinctly.
- Source title, statement, examples, constraints, tags, URL, and retrieval provenance are preserved.

### 2. Learning path contracts
- `solve` returns a valid `SolutionLearningPlan`.
- `prerequisites` returns valid concepts, dependency references, and a dependency-valid order.
- Prerequisite output does not include the full target solution by default.
- Invalid model output is rejected and can only be retried within a bounded policy.

### 3. Workflow behavior
- Lookup failure never invokes a teaching model.
- Exactly one selected learning path runs per request.
- A generation failure does not discard already fetched problem details.
- Both paths are covered with fake source adapters and fake model clients.

## Current legacy prototype tests

Run the existing tests from the repository root:

```powershell
.\\.venv\\Scripts\\python.exe -m unittest backend.test.test_intent_analyzer_agent -v
.\\.venv\\Scripts\\python.exe -m unittest discover -s backend/test -p "test_*.py" -v
.\\.venv\\Scripts\\python.exe -m compileall -q backend
```

The existing intent-agent tests use a fake LLM and do not make API requests or require a configured API key. These are regression tests for the preserved prototype, not proof that the LeetCode MVP is implemented.


## Six-agent workflow schema tests

New strict contract tests live in backend/test/test_workflow_schemas.py. They verify invalid problem IDs, required complexity derivations and required solution code. Run them with the full test suite:

~~~powershell
python -m compileall -q backend
python -m unittest discover -s backend/test -p "test_*.py" -v
~~~

End-to-end tests still require valid Gemini/Groq credentials, a retrievable LeetCode problem, Manim, FFmpeg and a working local TTS voice. Provider fallback should also be exercised by temporarily using an invalid Gemini key with a valid Groq key; never commit credentials.
