# Didactics — Software Requirements Specification

**Version:** 2.1  
**Status:** Focused personalized visual-learning MVP  
**Date:** 2026-11-09

## 1. Purpose

Didactics is a LeetCode-focused tutor that starts from a problem number and produces a personalized learning experience. After retrieving the canonical problem details, the learner chooses a programming language, independently sets DSA and programming proficiency, and chooses one of two intents:

1. **Solve this problem:** learn the reasoning, algorithm, complexity and implementation.
2. **Teach me the prerequisites:** learn the concepts required before attempting the problem.

The experience includes an algorithm animation pipeline. A structured algorithm trace is converted into a validated storyboard, rendered by a renderer adapter (Manim is the initial target), checked for quality, and attached to the lesson. Textual teaching must remain usable if animation rendering fails.

## 2. Product goals and success criteria

- Problem number is the primary input.
- Canonical question facts are fetched from a source adapter, never hallucinated by the teaching model.
- The learner configures language and two independent proficiency dimensions.
- Both learning intents are distinct and personalized.
- Beginner programming proficiency receives explicit explanations of syntax used in the generated code.
- Algorithm traces power both written dry runs and animation, keeping them consistent.
- Animation is generated from a typed storyboard and safe renderer templates.
- Render failures degrade gracefully to text/code lessons.

## 3. Scope

### 3.1 Included
- LeetCode problem-number input, lookup, normalization and confirmation.
- Language selection: Java, Python, C, C++.
- DSA proficiency: Beginner, Intermediate, Advanced.
- Programming proficiency: Beginner, Intermediate, Advanced.
- Solve and prerequisite learning paths.
- Language-specific code and proficiency-aware syntax explanations.
- Canonical algorithm trace.
- Structured storyboard generation and validation.
- Initial Manim renderer adapter, render worker, QA and artifact playback.
- Caching, bounded retries, error states and automated tests.

### 3.2 Deferred
- Other coding platforms and natural-language topic discovery.
- User accounts, progress dashboards, social features and leaderboards.
- Automatic code submission/judging.
- TTS, voice narration, avatar presenters and advanced video editing.
- Unrestricted multi-agent orchestration.
- Arbitrary model-generated code execution.

## 4. Learner journey and settings

1. Enter a positive LeetCode problem number.
2. Retrieve and review canonical problem details.
3. Select one language: Java, Python, C, or C++.
4. Select DSA proficiency: Beginner, Intermediate, or Advanced.
5. Select programming proficiency: Beginner, Intermediate, or Advanced.
6. Select Solve or Prerequisites.
7. Receive tailored teaching content, code/examples, and animation when enabled.
8. Play, pause, step through, and replay the animation; continue using text/code if rendering is unavailable.

### FR-01 — Language selection
The system shall support Java, Python, C and C++. The selected language shall be used consistently for solution code, prerequisite examples, syntax annotations, code labels and language-specific discussion. Unsupported language values shall be rejected.

### FR-02 — Independent proficiency selection
The system shall collect two independent levels:
- `dsa_proficiency`: `beginner | intermediate | advanced`
- `programming_proficiency`: `beginner | intermediate | advanced`

The system shall not infer one from the other. All combinations must be valid, including advanced programming with beginner DSA and beginner programming with advanced DSA.

### FR-03 — Programming-level adaptation
- **Beginner:** explain syntax used in the actual code. Cover relevant declarations, types, assignments, loops, conditionals, methods/functions, arrays/collections, pointers/references, memory behavior and library APIs as appropriate to the selected language. Include annotated code and small syntax examples where helpful.
- **Intermediate:** explain non-obvious syntax, language APIs, data representation and language-specific trade-offs. Avoid unnecessary explanations of elementary constructs.
- **Advanced:** prefer idiomatic concise code and focus on subtle language behavior, algorithmic trade-offs and performance.
- Explanations shall be scoped to constructs used by the current lesson, not become a generic language course.

### FR-04 — DSA-level adaptation
- **Beginner:** define core terminology, explain prerequisite concepts and derive the approach incrementally.
- **Intermediate:** assume common structures/algorithms but explain important observations and trade-offs.
- **Advanced:** focus on invariants, proof, complexity, optimizations and alternatives.
- The system shall adapt explanation depth without changing the correctness of the algorithm.

## 5. Problem retrieval requirements

### FR-05 — Input and lookup
- Accept a positive integer problem number.
- Reject blank, malformed, zero and negative values before source access.
- Fetch from a dedicated problem-source adapter.
- Normalize number, slug, title, difficulty, statement, examples, constraints, topic tags, canonical URL, source name and retrieval time.
- Distinguish not-found, upstream-unavailable, rate-limited and malformed-source outcomes.
- Do not invoke teaching or animation generation if lookup fails.

### FR-06 — Confirmation
Display the retrieved title, difficulty, statement, examples, constraints, tags and canonical URL before teaching. Allow the learner to return and enter another number. Missing optional fields must be explicitly represented.

## 6. Learning intent requirements

### FR-07 — Intent selection
The learner shall explicitly select `solve` or `prerequisites`. The backend shall execute only the selected path. No default path shall be silently selected.

### FR-08 — Solve path
The output shall include:
- Task restatement and input/output model.
- Constraints and key observations.
- Brute-force baseline when useful.
- Optimized approach derivation and algorithm steps.
- Correctness rationale or proof outline.
- Time and space complexity with justification.
- Selected-language implementation.
- Programming-proficiency-aware syntax explanations.
- Worked sample trace and relevant edge cases.
- Structured trace states suitable for animation.

### FR-09 — Prerequisite path
The output shall include:
- Problem-specific prerequisite concepts.
- Dependency graph and dependency-valid learning order.
- Explanation of why each concept matters to the target problem.
- Concept lesson and standalone example for each concept.
- Selected-language examples and proficiency-aware syntax explanations.
- Knowledge checks and expected answers.
- Final mapping from concepts to the target problem.
- No complete target solution by default.

## 7. Animation requirements

### FR-10 — Shared trace
The system shall create a language-independent `AlgorithmTrace` from the solution walkthrough. The written dry run and animation shall consume the same trace data. Concept lessons may create smaller concept traces when animation is pedagogically useful.

### FR-11 — Storyboard generation
The animation planner shall transform validated trace data into a structured storyboard. Each storyboard shall define:
- Version and source lesson/trace reference.
- Scenes with IDs, titles, purpose and duration.
- Visual objects with stable IDs, types, labels and initial states.
- Ordered steps with source trace-state references.
- State changes, highlights, pointers/index movement and captions.
- Transitions and durations.
- Render profile: resolution, frame rate, theme and output format.

### FR-12 — Storyboard validation
- Validate the storyboard against a strict schema.
- Validate object references and transition consistency.
- Ensure every animation step maps to an actual trace state.
- Reject malformed storyboards before rendering.
- Allow only bounded schema-repair attempts.

### FR-13 — Rendering
- The initial renderer shall use a Manim adapter behind a renderer interface.
- Rendering shall run asynchronously in an isolated worker.
- Renderer instructions shall be produced from trusted scene templates and validated structured data.
- Arbitrary model-generated shell commands or unrestricted Python shall never be executed.
- Enforce CPU, memory, wall-time, output-size and frame-count limits.
- Persist the storyboard, video and render metadata.

### FR-14 — Render QA
Validate:
- Output exists and decodes.
- Duration and frame count are non-zero.
- Dimensions and frame rate match the requested profile.
- Captions remain readable and within safe areas.
- No blank/missing scenes, missing visual objects or unexpected clipping.
- Artifact is linked to the exact storyboard and trace version.

Failed renders shall receive bounded retries. After retries are exhausted, animation status shall be failed/unavailable while the textual lesson remains available.

### FR-15 — Animation playback
The client shall support play, pause, replay and step/scene navigation where the artifact format supports it. It shall show render status and never display a broken playback URL as ready.

## 8. API contracts

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Service health |
| GET | `/api/problems/{number}` | Retrieve canonical problem |
| POST | `/api/learning-sessions` | Create personalized learning session |
| GET | `/api/learning-sessions/{session_id}` | Retrieve session and generation status |
| GET | `/api/animations/{animation_id}` | Retrieve animation status and artifact metadata |

Example request:

```json
{
  "problem_number": 1,
  "intent": "solve",
  "language": "java",
  "dsa_proficiency": "beginner",
  "programming_proficiency": "beginner",
  "animation": true
}
```

## 9. Core data contracts

- **ProblemDetails:** canonical problem fields and source provenance.
- **LearnerConfig:** language enum, DSA proficiency enum, programming proficiency enum.
- **LearningSessionRequest:** problem number, intent, learner config, animation preference.
- **SolutionLearningPlan:** observations, approach, proof, complexity, implementation, syntax annotations, examples and trace.
- **PrerequisiteLearningPath:** concept nodes, dependency edges, learning order, examples, checks and target-problem bridge.
- **AlgorithmTrace:** ordered language-independent states and operations.
- **AnimationStoryboard:** versioned scenes, objects, steps, transitions, captions and render profile.
- **AnimationJob:** job ID, status, attempts, timestamps and diagnostics.
- **AnimationArtifact:** artifact URI, format, duration, dimensions, frame rate, storyboard/trace versions and QA report.
- **LearningSession:** problem, intent, learner configuration, lesson artifacts and animation status.

## 10. Non-functional requirements and guardrails

### Correctness and provenance
- Source adapter owns canonical question facts.
- LLM explains; it does not invent missing source facts.
- Written walkthrough and animation use the same trace version.

### Safety
- Treat problem text as untrusted data.
- Never execute unrestricted LLM-generated code.
- Use trusted renderer templates and schema-validated data.
- Isolate render workers and enforce resource limits.
- Keep credentials out of source control and logs.

### Reliability
- Bounded retries and timeouts for external services.
- Persist job state and diagnostics.
- Animation failure must not invalidate a successful lesson.
- Never mark an empty or corrupt video as successful.

### Usability
- Language and both proficiency axes are visible and editable before generation.
- The two intents are clearly distinct.
- Beginner programming users receive syntax explanations for their selected language.
- Text and code remain accessible when animation is unavailable.

## 11. Testing and acceptance criteria

- Lookup tests cover valid, invalid, missing, rate-limited and unavailable problems.
- Configuration tests cover all four languages and all 3×3 proficiency combinations.
- Prompt/contract tests verify language-specific code and independent proficiency adaptation.
- Beginner syntax tests verify explanations for constructs actually present in the generated code.
- Workflow tests prove only one selected learning path executes.
- Prerequisite tests verify dependency order and absence of solution spoilers.
- Trace tests verify deterministic state ordering.
- Storyboard tests verify schema, references and trace consistency.
- Renderer tests use small fixture scenes and cover success, timeout, crash and corrupt output.
- QA tests cover empty frames, clipping, invalid dimensions and duration.
- End-to-end tests cover lookup → config → solve/prerequisites → lesson → animation status.
- Animation failure tests verify the text lesson remains usable.

The MVP is accepted when a learner can enter a problem number, configure language and both skill levels, choose either learning intent, and receive a validated personalized lesson with an animation artifact when rendering succeeds.

## 12. Delivery roadmap

1. Canonical problem lookup and normalized schema.
2. Learner configuration and UI.
3. Solve and prerequisite workflows.
4. Language-specific code and beginner syntax explanations.
5. Shared algorithm trace and fixture-based tests.
6. Typed storyboard planner and validation.
7. Isolated Manim renderer, asynchronous job lifecycle and QA.
8. Animation player, failure fallback and end-to-end acceptance tests.
