# Running Didactics

The focused MVP has a FastAPI backend and a React/Vite frontend. The previous request-understanding prototype and CLI remain available separately.

## Prerequisites

- Python 3.10+
- Node.js 18+
- npm

## 1. Start the API

From the repository root:

\`\`\`powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
\`\`\`

Check \`http://127.0.0.1:8000/health\`. Interactive API docs: \`http://127.0.0.1:8000/docs\`.

## 2. Start the frontend

In a second terminal:

\`\`\`powershell
cd frontend
npm install
npm run dev
\`\`\`

Open the Vite URL (normally \`http://localhost:5173\`). Vite proxies \`/api\` and \`/health\` to FastAPI.

## Problem lookup

\`GET /api/problems/{number}\` resolves the numeric ID through LeetCode's public problem index, retrieves question details through LeetCode GraphQL, sanitizes statement HTML, and returns normalized source fields. Successful lookups are cached in memory for five minutes. Missing IDs, premium-only statements, source rate limits and upstream failures have separate API errors.

## Learner configuration

\`POST /api/learner-config/validate\` validates the language and independent DSA/programming levels. Beginner programming proficiency enables explicit syntax guidance.

## Tests

\`\`\`powershell
python -m unittest backend.test.test_problem_lookup -v
python -m unittest discover -s backend/test -p "test_*.py" -v
\`\`\`

LeetCode is an external source and may rate-limit or change its public endpoints. Source failures are surfaced as errors, never as successful problem lookups.


## Six-agent solve-to-video workflow (target architecture)

1. **Agent 1 — Solution strategist:** brute-force-first solution ladder, optimized variants, alternative algorithms and selected-language code.
2. **Agent 2 — Complexity analyst:** time/space derivation for every code variant.
3. **Agent 3 — Lesson director:** scene timeline with exact narration, on-screen content, visual direction and timing.
4. **Agent 4 — Manim animator:** planned scenes and scene-boundary/render metadata.
5. **Agent 5 — Audio producer:** one narration segment per scene with duration, transcript identity and audio metadata.
6. **Agent 6 — Multimodal QA director:** watches and listens to the composed output, checks it against the plan and source artifacts, and issues repair tickets.

Agents 4 and 5 produce media in parallel after Agent 3's plan is approved. Agent 6 is the release gate. Visual tickets route to Agent 4; audio tickets route to Agent 5. Reopen Agent 3 only when the plan itself is defective. The default target is at most three QA repair cycles; exhaustion marks media as needs_review or failed while preserving the text lesson and diagnostics.

Artifact hand-offs: SolutionPortfolio → ComplexityReport → ScenePlan → (AnimationBundle + AudioBundle) → QAReport → MediaManifest.

This is the approved target architecture. Do not infer that Agent 1–6, Manim rendering, TTS generation, media composition or audiovisual QA are implemented merely because these requirements are documented.
