# Didactics — Software Requirements Specification

**Version:** 2.0  
**Status:** Focused MVP baseline  
**Date:** 2026-11-09

## 1. Purpose

Didactics is a LeetCode-focused learning agent. The learner supplies a LeetCode problem number. The system retrieves the canonical problem details, presents them to the learner, and asks them to choose one of two learning goals:

1. **Solve the problem** — learn how to derive and implement a solution.
2. **Learn the prerequisites** — learn the foundational concepts needed to solve the problem before seeing the solution.

This SRS deliberately narrows the previous broad educational-video vision to one end-to-end workflow. The existing implementation is preserved on `archive/current-project-2026-11`; the main branch defines the new product baseline.

## 2. Goals and success criteria

### 2.1 Goals
- Make a problem number the primary and sufficient input for the initial lookup.
- Retrieve problem metadata from a canonical source rather than asking an LLM to guess it.
- Let the learner inspect and confirm the problem before generation.
- Provide two distinct, explicit learning paths.
- Produce structured, validated educational artifacts.
- Keep external services replaceable and tests deterministic.
- Ship a narrow, usable workflow before expanding to other coding platforms or learning topics.

### 2.2 MVP acceptance criteria
- A valid supported problem number returns its matching title and problem metadata.
- Invalid and unknown numbers return clear errors without calling the teaching model.
- The details view shows source provenance and makes unavailable optional fields explicit.
- The learner can select either Solve or Prerequisites after lookup.
- Selecting Solve generates a solution-focused learning artifact only.
- Selecting Prerequisites generates a dependency-ordered curriculum and does not reveal the complete solution by default.
- Both artifacts are schema validated before being returned.
- Upstream and LLM failures preserve the already retrieved problem context.

## 3. Scope

### 3.1 In scope
- LeetCode problem number input and validation.
- Canonical problem lookup and normalization.
- Problem summary/confirmation.
- Solve-vs-prerequisites selection.
- Structured solution teaching.
- Structured prerequisite teaching.
- Configurable LLM provider/model integration.
- Caching, timeouts, bounded retries, source attribution, and tests.

### 3.2 Out of scope for this MVP
- Free-form topic or natural-language problem discovery.
- Other coding platforms.
- User accounts, profiles, streaks, badges, leaderboards, social features, and detailed progress analytics.
- Automatic code submission or judging on LeetCode.
- Manim animations, TTS, generated videos, subtitles, and media storage.
- Broad autonomous internet research.
- Multiple parallel agents for tasks that can be handled by one bounded generator or deterministic service.

## 4. Users and primary use cases

**Primary user:** A learner practicing algorithmic problem solving who may either want a guided solution or need to fill conceptual gaps first.

| ID | Use case | Expected result |
|---|---|---|
| UC-01 | Enter a problem number | System validates the number and looks up the problem |
| UC-02 | Inspect the problem | System displays canonical statement, examples, constraints, difficulty, tags and URL when available |
| UC-03 | Choose Solve | System generates a structured solution walkthrough |
| UC-04 | Choose Prerequisites | System generates a concept curriculum in dependency order |
| UC-05 | Recover from lookup failure | Learner sees a retryable error; no fabricated details |
| UC-06 | Recover from generation failure | Learner retains problem details and can retry the selected learning path |

## 5. User journey

1. Learner opens Didactics.
2. Learner enters a numeric LeetCode problem ID.
3. Client validates basic input shape and requests the problem.
4. Backend validates range/format and calls the problem-source adapter.
5. Adapter retrieves canonical problem data and maps it into a normalized schema.
6. UI shows title, difficulty, statement, examples, constraints, tags, and canonical URL where available.
7. Learner chooses **Solve this problem** or **Teach me the prerequisites**.
8. Backend dispatches only the selected path.
9. The teaching generator returns a structured result.
10. Backend validates the result and returns it as a learning session.
11. Learner can retry generation or return to problem selection.

## 6. Functional requirements

### FR-01 — Problem-number input
- The system shall accept a positive integer problem number.
- The system shall reject blank, non-numeric, negative, and malformed values.
- The initial UX shall not require title search or a natural-language prompt.

### FR-02 — Problem lookup
- The backend shall query a dedicated problem-source adapter.
- The adapter shall return normalized data with canonical source URL/identifier.
- The system shall distinguish not-found, upstream-unavailable, rate-limited, and malformed-source responses.
- The system shall not infer a problem statement from the number with an LLM.

### FR-03 — Problem details
The normalized result should include:
- Number and slug (when available).
- Canonical title.
- Difficulty.
- Full statement/description.
- Examples and explanations.
- Constraints.
- Topic tags.
- Canonical URL.
- Source name and retrieval timestamp.

Optional fields may be absent. Required fields for a valid details screen are problem number, title, statement (or explicitly supported statement representation), and canonical source reference.

### FR-04 — Problem confirmation
- The system shall show retrieved details before generating teaching content.
- The learner shall be able to return and enter another problem number.
- The system shall clearly distinguish source-provided metadata from Didactics-generated content.

### FR-05 — Learning-path choice
The UI shall offer exactly two first-class actions:
- `solve`
- `prerequisites`

The selected intent shall be explicit in the API request. The default shall not silently choose a path.

### FR-06 — Solve learning path
The output shall contain:
- Problem restatement and input/output model.
- Constraints analysis.
- Key observations.
- Brute-force baseline when pedagogically useful.
- Selected approach and why it works.
- Ordered algorithm steps or pseudocode.
- Worked example with intermediate states.
- Correctness intuition or proof outline.
- Time and space complexity with justification.
- Implementation in the requested/configured language.
- Relevant edge cases.

The generator should avoid spoiling the complete implementation before explaining the approach. The UI may progressively reveal sections in teaching order.

### FR-07 — Prerequisite learning path
The output shall contain:
- A set of prerequisite concepts tailored to the problem.
- A dependency graph or explicit prerequisite relationships.
- A topologically ordered learning sequence.
- Why each concept is required for this problem.
- A concise explanation and a standalone example for each concept.
- A short knowledge check or practice prompt for each concept.
- A final mapping from the concepts to the target problem.

The path shall not reveal the complete target solution by default. A learner must explicitly switch to the Solve path to request it.

### FR-08 — Learning level and language
- The first implementation may use a configured default learner level and programming language.
- The API shall allow optional overrides.
- Unknown values shall be represented explicitly rather than guessed.

### FR-09 — Structured output
- Pydantic models shall validate all generated artifacts.
- Invalid output shall be rejected and may receive a bounded repair attempt.
- The API shall never return a partial artifact as successful without marking it partial.

### FR-10 — Error handling
- Errors shall include a stable error code, a user-safe message, and whether retry is appropriate.
- API keys and internal provider error payloads shall not be exposed.
- The original problem result shall remain available when a later generation operation fails.

## 7. External interfaces

### 7.1 API endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Liveness/readiness summary |
| GET | `/api/problems/{number}` | Retrieve normalized LeetCode problem details |
| POST | `/api/learning-paths` | Generate one selected learning path |

Example request:

```json
{
  "problem_number": 1,
  "intent": "prerequisites",
  "language": "java",
  "learner_level": "beginner"
}
```

Example response envelope:

```json
{
  "problem": {
    "number": 1,
    "title": "Two Sum",
    "difficulty": "Easy",
    "canonical_url": "https://leetcode.com/problems/two-sum/"
  },
  "intent": "prerequisites",
  "learning_artifact": {},
  "status": "completed"
}
```

The values above illustrate the contract only. The live lookup is responsible for supplying real problem metadata.

### 7.2 Problem source adapter
- Hide source-specific endpoints, payloads, authentication and parsing behind an interface.
- Record the upstream URL/identifier and retrieval time.
- Apply timeout and bounded retry policies.
- Add caching using canonical problem identity and a source freshness policy.
- Treat upstream text as untrusted content; it is data, not executable instructions.

### 7.3 LLM provider adapter
- Reuse the current provider configuration abstraction where suitable.
- Keep model selection explicit and provider-specific.
- Validate model output against a strict schema.
- Ensure prompts treat problem statements and examples as untrusted input data.
- Do not log credentials or expose hidden chain-of-thought.

## 8. Core data contracts

### ProblemDetails
- `number: positive integer`
- `slug: optional string`
- `title: non-empty string`
- `difficulty: Easy | Medium | Hard | Unknown`
- `statement: non-empty string`
- `examples: list[ProblemExample]`
- `constraints: list[string]`
- `topic_tags: list[string]`
- `canonical_url: valid URL`
- `source_name: string`
- `retrieved_at: timestamp`

### LearningPathRequest
- `problem_number: positive integer`
- `intent: solve | prerequisites`
- `language: optional string`
- `learner_level: beginner | intermediate | advanced | unknown`

### SolutionLearningPlan
- `problem_summary`
- `input_output_model`
- `constraints_analysis`
- `observations`
- `approach`
- `algorithm_steps`
- `pseudocode`
- `worked_trace`
- `correctness_rationale`
- `time_complexity`
- `space_complexity`
- `implementation`
- `edge_cases`

### PrerequisiteLearningPath
- `problem_summary`
- `concepts[]`: concept ID, name, why needed, prerequisite IDs, explanation, example, check question and expected answer.
- `learning_order[]`: concept IDs in dependency-valid order.
- `problem_connection`: how the prerequisite concepts support solving this problem.
- `solution_spoiler_included: false` by default.

## 9. Architecture and design constraints

- Keep problem fetching and teaching generation separate.
- Canonical facts come from the source adapter; LLMs explain but do not invent source facts.
- Use deterministic code for validation, normalization, ordering, caching and retries.
- Keep agents bounded to one clear pedagogical responsibility.
- Prefer a small explicit workflow over a large multi-agent graph for the first milestone.
- Preserve source provenance through every stage.
- Keep the app independently testable without live LeetCode or LLM calls.

## 10. Non-functional requirements

### Performance
- Problem lookup should use bounded network timeouts.
- Cache frequently requested problem metadata.
- Generation is asynchronous-ready but synchronous response is acceptable for the first vertical slice if provider latency is manageable.

### Reliability
- External requests have bounded retries and clear failure classification.
- A model/provider failure must not discard a successful lookup.
- No fabricated problem data on source errors.

### Security
- Secrets are environment-configured and never committed.
- Retrieved statements are treated as untrusted data.
- No arbitrary code execution or code submission in this milestone.
- Errors and logs redact credentials and sensitive provider payloads.

### Maintainability
- Provider and problem source are behind adapters.
- Schemas are versionable and strict.
- Tests use fake adapters and fake models.

### Accessibility and usability
- The two learning choices must be visually and semantically distinct.
- Problem details must remain readable on mobile and desktop.
- Errors must explain how to recover.

## 11. Testing requirements

- Unit tests for numeric input validation and problem normalization.
- Contract tests for not-found, rate-limited, unavailable and malformed-source responses.
- Schema tests for both learning artifact types.
- Prompt tests confirming problem statement content is treated as data.
- Workflow tests verifying only the selected path executes.
- Tests confirming prerequisite output contains no full solution by default.
- End-to-end tests for valid lookup → confirmation → solve path.
- End-to-end tests for valid lookup → confirmation → prerequisite path.
- Regression tests for current provider configuration behavior when reused.

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| LeetCode source changes | Isolate source access behind adapter and maintain fixtures |
| Rate limits or blocked upstream requests | Timeout, bounded retry, cache, clear unavailable state |
| Incorrect LLM-generated explanations | Structured output, test fixtures, explicit correctness section |
| Prerequisite path becomes generic | Require per-concept rationale linking concept to problem |
| Prerequisite flow spoils solution | Explicit spoiler constraint and regression tests |
| Scope expands too early | Enforce the deferred-scope list until MVP acceptance criteria pass |

## 13. Implementation roadmap

### Milestone 1 — Problem retrieval
- Define source adapter and `ProblemDetails`.
- Implement numeric validation and lookup endpoint.
- Add normalization, attribution, caching and deterministic tests.

### Milestone 2 — Problem review and intent selection
- Build details/confirmation screen.
- Add explicit Solve and Prerequisites actions.
- Add request/response contracts.

### Milestone 3 — Solve learning path
- Implement `SolutionLearningPlan`.
- Generate and validate a solution explanation.
- Add traces, complexity reasoning and implementation output.

### Milestone 4 — Prerequisite learning path
- Implement concept/dependency schema.
- Generate the learning sequence and examples.
- Validate ordering and prevent solution spoilers.

### Milestone 5 — End-to-end hardening
- Failure-state UX, caching, observability and integration tests.
- Confirm the MVP acceptance criteria before adding other capabilities.

## 14. Definition of done

The first milestone is complete when a learner can enter a valid LeetCode problem number, verify the correct problem details, choose either Solve or Prerequisites, and receive the corresponding validated learning experience. All failure cases must be explicit and tested. No video pipeline or broad free-form learning mode is required for this release.
