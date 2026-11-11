# Running Didactics

## Existing API

Start the backend from the repository root:

~~~powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --reload --port 8000
~~~

Start the frontend in a second terminal:

~~~powershell
cd frontend
npm install
npm run dev
~~~

API docs: http://localhost:8000/docs

## Six-agent generation setup

Create the local file backend/.env using backend/.env.example. Do not commit it.

- GEMINI_API_KEY — primary provider.
- GROQ_API_KEY — automatic provider fallback.
- Optional GEMINI_API_KEY_FALLBACK_1 and GROQ_API_KEY_FALLBACK_1 for key rotation.

Default models: gemini-3.6-flash and qwen/qwen3.8-27b. Override GEMINI_MODEL or GROQ_MODEL if these model IDs are unavailable to your account. API keys are never written to run artifacts or logs.

### Media prerequisites

Manim requires FFmpeg and native dependencies. Install FFmpeg and add it to PATH. On Windows, install a LaTeX distribution such as MiKTeX if required by your Manim installation. If native Manim dependencies fail on Windows, use WSL2/Ubuntu and install the Python requirements there.

Agent 5 uses pyttsx3 for local/offline speech generation. Windows uses an installed SAPI voice; no separate TTS API key is required.

### Six-agent API

From a second terminal, start the frontend:

~~~powershell
cd frontend
npm install
npm run dev
~~~

The frontend Build my learning session action calls POST /api/sessions/generate. The API fetches the problem and executes:

1. Agent 1: brute-force-first solution portfolio, optimization ladder and algorithm alternatives.
2. Agent 2: time/space derivations for every code variant.
3. Agent 3: scene timeline, exact narration and visual directions.
4. Agent 4: Manim animation.
5. Agent 5: per-scene audio generation. Agents 4 and 5 run in parallel.
6. Agent 6: video frame/metadata inspection, audio transcription with Groq Whisper when configured, and structured release assessment.

The workflow runs synchronously in a worker thread for now. Long-running job polling and cancellation are a later operational enhancement. Agent 6 can reject the media and route repair tickets to Agents 4 and 5; the orchestrator allows at most three render/audio/QA cycles and then marks the run needs_review rather than looping forever.

### Checkpoints and logs

All generated output is local and ignored by Git:

- out/logs/didactics.log — terminal-mirrored application logs.
- out/runs/<run_id>/checkpoints/00_input_validated.json — validated input.
- 01_solution_portfolio.json
- 02_complexity_report.json
- 03_scene_plan.json
- 04_animation_bundle.json or 04_animation_error.json
- 05_audio_bundle.json or 05_audio_error.json
- 05_media_composition.json
- 06_qa_report.json
- failure.json — traceback and completed stages if orchestration fails.
- result.json and manifest.json — final status and artifact inventory.

Generated media is served from /artifacts/runs/<run_id>/.... Never commit .env, API keys, generated media or checkpoints.

### Error handling and QA limitations

Every provider attempt and workflow exception is logged to the terminal and out/logs/didactics.log. Stage-specific failures and tracebacks are preserved in the run directory. Gemini is attempted first; configured Gemini keys are rotated before Groq fallback. Groq keys are rotated before the workflow fails. All agent JSON is validated against strict Pydantic schemas.

Agent 6 probes media files, samples video frames for blank-frame signals, and uses Groq Whisper transcription when a Groq key is configured. If transcription is unavailable, speech-content verification is explicitly marked skipped. This is technical QA, not human-level review of visual pedagogy, animation quality or voice naturalness. A missing media dependency results in needs_review while retaining completed text artifacts.

### Tests

~~~powershell
python -m compileall -q backend
python -m unittest discover -s backend/test -p "test_*.py" -v
~~~


## Code organization

- Agent code: `backend/app/agents/agent modules` (one module per agent).
- Agent prompts: `backend/app/prompts/agent_*.txt`.
- Schemas: `backend/app/schemas/workflow.py`.
- Run/output storage: `backend/app/storage/out_manager.py`.
- Checkpoints/failures: `backend/app/storage/checkpoint_manager.py`.

Agent 1 receives only the statement, examples, and constraints as problem context, plus the three required learner settings separately. A focused unit test verifies that title, difficulty, tags, metadata and unrelated learner fields are excluded.
