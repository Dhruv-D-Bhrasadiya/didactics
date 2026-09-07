# Didactics — Software Requirements Specification (SRS)

**Version:** 1.0
**Status:** Proposed target architecture
**Date:** 2026-09-07

---

## 1. Purpose

Didactics is an autonomous educational-content generation system that accepts a learner's natural-language request and produces a synchronized audio-visual explainer. The target system should transform an ambiguous learning request into a pedagogically structured lesson, visual storyboard, executable Manim animation, narration, subtitles, and a final video asset.

This document defines the target architecture, responsibilities of each agent, contracts between stages, validation strategy, workflow state, failure handling, and implementation roadmap. It intentionally contains no implementation code.

The repository currently implements only the Intent Analyzer Agent as a working prototype. The remaining components described here are target-state requirements, not claims that they already exist.

---

## 2. Current Repository Assessment

The current repository has a good foundation for an agent-oriented system. The concrete implementation includes a reusable `BaseAgent`, provider-specific LLM builders, API-key rotation, prompt loading, JSON parsing, Pydantic validation, an `IntentAnalyzerAgent`, its `IntentAnalysis` schema, and unit tests. The current agent accepts a learner query and returns structured intent information. The project documentation also describes the intended end-to-end product as an explainer-video generator.

The most important architectural gap is that the current `diagram.md` describes a much larger multi-agent system than the codebase currently implements. This is normal for an early design, but it creates a risk: adding agents one-by-one without stable contracts will make the system difficult to reason about.

The target design therefore follows a **contract-first, workflow-first** approach:

- Define the artifact produced by every stage before implementing the agent.
- Use LangGraph for orchestration, branching, retries, checkpoints, and workflow state.
- Use LLM agents only where interpretation, planning, synthesis, or generation is required.
- Use deterministic services for validation, rendering, media composition, storage, and other operations where an LLM adds no value.
- Make failures local and recoverable rather than restarting the complete pipeline.

---

## 3. Product Vision

A learner should be able to submit a request such as:

> Teach me binary search in Java as if I am a beginner. Show an example and explain the time complexity.

Didactics should determine:

1. What the learner is asking for.
2. Who the learner is and what level of explanation is appropriate.
3. What concepts must be taught first.
4. What lesson structure will best teach the topic.
5. Which examples and execution traces will make the concept understandable.
6. Which parts should become visual scenes.
7. How those scenes should be animated.
8. What should be narrated.
9. How narration, visuals, and captions should align.
10. Whether the generated content is correct and executable.
11. How to repair failures without unnecessarily regenerating valid work.
12. How to package and deliver the final explainer video.

The system should behave less like a single chatbot and more like an educational production pipeline controlled by an intelligent workflow engine.

---

## 4. Goals

### 4.1 Primary goals

- Convert natural-language educational requests into structured learning specifications.
- Produce pedagogically coherent explanations rather than arbitrary generated text.
- Generate visual explanations for algorithms, mathematics, programming concepts, and related technical subjects.
- Generate executable Manim animations from a structured visual plan.
- Generate narration and captions synchronized with the visual timeline.
- Validate generated artifacts before expensive rendering and delivery.
- Recover from model, code, rendering, content, and synchronization failures.
- Preserve intermediate artifacts so jobs can be resumed or selectively regenerated.
- Support multiple LLM providers without coupling business logic to one provider.
- Provide observable, debuggable workflows.

### 4.2 Secondary goals

- Cache equivalent or reusable results where appropriate.
- Support user requests to simplify, expand, regenerate, or correct a previous explanation.
- Allow future support for multiple media types, not only Manim videos.
- Make individual agents independently testable.

### 4.3 Non-goals for the first production milestone

- Fully autonomous research over the entire internet.
- Arbitrary execution of untrusted user-generated programs.
- Perfect educational personalization based on long-term learner psychology.
- Real-time video generation during every API request.
- A large number of specialized agents solely for architectural appearance.

---

## 5. Core Design Principle: Agent vs Service

A major requirement is to distinguish an **agent** from a **service/tool**.

### Agent

An agent is appropriate when the system must interpret, decide, plan, synthesize, or generate something whose solution is not deterministic.

Examples:

- Intent analysis.
- Lesson planning.
- Concept explanation.
- Visual planning.
- Manim code generation.
- Narration generation.
- Targeted code repair.

### Deterministic service/tool

A normal service is appropriate when the operation has a well-defined deterministic procedure.

Examples:

- Pydantic/schema validation.
- Python syntax checking.
- Running a Manim render.
- Generating audio through a TTS API.
- Combining media with FFmpeg.
- Storing artifacts.
- Computing hashes and cache keys.
- Reading job state.

This distinction should be maintained throughout implementation. Do not create an LLM agent for a task that can be reliably performed by ordinary software.

---

## 6. High-Level Architecture

The target system consists of these layers:

1. **Client Layer** — learner interface and video playback.
2. **API Layer** — accepts requests, creates jobs, exposes status and results.
3. **Workflow Layer** — LangGraph state machine and orchestration logic.
4. **Agent Layer** — bounded reasoning and generation components.
5. **Validation Layer** — deterministic and semantic quality gates.
6. **Execution Layer** — Manim, TTS, FFmpeg, caption processing, thumbnails.
7. **Persistence Layer** — job metadata, checkpoints, cache, and generated assets.
8. **LLM Provider Layer** — Gemini, Groq, OpenAI, and future providers.

The conceptual pipeline is:

**User Request → Understanding → Pedagogical Plan → Educational Content → Visual Storyboard → Asset Generation → Validation → Rendering → Media Composition → Delivery**

With revision loops entering the pipeline at the stage where the failure occurred.

---

## 7. End-to-End Workflow

### 7.1 Request creation

The user submits a natural-language learning request.

Input examples:

- "Explain recursion in Python."
- "Teach me binary search to a beginner and show a visual example."
- "Explain backpropagation mathematically with an intuitive animation."

The API creates a job identifier and records the original request.

### 7.2 Cache lookup

The system computes a normalized request/cache key and checks whether a suitable completed result already exists.

A cache hit may return an existing result immediately. A cache miss starts a new workflow.

### 7.3 Request understanding

The Intent Analyzer identifies the user's goal, topic, domain, expected depth, audience, requested deliverables, and initial learning structure.

Additional scope analysis and concept mapping may refine the result.

### 7.4 Pedagogical planning

The system decides what should be taught, in which order, why each section is needed, and what the learner should understand by the end.

### 7.5 Educational content generation

The system creates the actual teaching material: explanations, algorithms/procedures, examples, edge cases, and execution traces where relevant.

### 7.6 Visual planning

The content is converted into a storyboard describing what appears on screen, how it changes, what is highlighted, and how long each scene should last.

### 7.7 Asset generation

The storyboard is converted into Manim code, narration, and caption information.

### 7.8 Validation

Artifacts pass schema, code, execution, content, and synchronization checks. Failed artifacts are routed to the smallest useful repair loop.

### 7.9 Rendering and composition

Approved animation code is rendered. Narration is synthesized. Video and audio are composed. Captions are attached. A thumbnail and final metadata are generated.

### 7.10 Delivery

The final assets are persisted and the API returns the result to the learner.

---

# 8. Agent Architecture

Every agent must be specified using the following contract:

- **Purpose** — why it exists.
- **Trigger** — when the workflow calls it.
- **Input** — exact upstream artifacts it consumes.
- **Processing responsibility** — what it decides or generates.
- **Output** — exact artifact it produces.
- **Consumer** — who uses the output.
- **Validation** — how output quality is checked.
- **Failure modes** — what can go wrong.
- **Recovery path** — where the workflow goes after failure.
- **State ownership** — which part of workflow state it writes.

The following agents are the recommended target architecture. Some can later be combined if practical; they should not be implemented as separate agents merely because they are listed separately.

---

## 9. Stage 1 — Request Understanding Agents

### 9.1 Intent Analyzer Agent

**Status:** Implemented prototype.

**Purpose:** Convert the learner's raw request into a structured representation of intent.

**Input:**

- Original user query.
- Optional user-provided constraints.
- Optional prior conversation/job context in future versions.

**Output:** `IntentAnalysis`-type artifact containing at minimum:

- Domain.
- Subdomain.
- Main topic.
- Subtopics.
- Modules.
- Roadmap.
- Deliverables.
- Degree of explanation.
- Audience.
- Learning objectives.
- Assumptions.

**Consumer:** Scope/requirements analysis and pedagogical planning.

**Important design rule:** The Intent Analyzer should not generate the complete lesson. It should understand the request and create a reliable handoff.

**Current implementation assessment:** The repository's Pydantic schema and validation approach are good. Provider abstraction and fallback-key rotation are also useful. The prompt should eventually be tightened so the model is explicitly instructed to avoid inventing unnecessary fields and to use controlled values where appropriate.

**Failure modes:**

- Empty query.
- Invalid JSON.
- Schema mismatch.
- Provider quota/rate-limit errors.
- Provider authentication errors.
- Provider timeout/unavailability.

**Recovery:**

- Reject invalid input immediately.
- Retry/rotate configured provider keys where appropriate.
- Retry transient provider errors with bounded attempts.
- Fail the stage with an observable error if structured output cannot be produced.

---

### 9.2 Scope & Requirements Agent

**Purpose:** Resolve ambiguities that the initial intent representation cannot safely decide.

**Input:**

- Original user request.
- Intent Analysis.

**Output:** `LearningRequirements` artifact containing:

- Target audience.
- Prior knowledge assumptions.
- Desired explanation depth.
- Programming language, if any.
- Desired duration range.
- Visual preference.
- Example requirements.
- Mathematical detail requirements.
- Output format requirements.
- Explicit constraints.
- Ambiguities requiring default assumptions.

**Consumer:** Curriculum planner, content agents, and visual planner.

**Failure:** If the request is too ambiguous for safe generation, the system should either apply documented defaults or ask the user a clarification question rather than hallucinating requirements.

---

### 9.3 Topic / Concept Mapper

**Purpose:** Convert the requested topic into a dependency-aware concept inventory.

**Input:** Intent Analysis + Learning Requirements.

**Output:** `ConceptMap` containing:

- Concepts.
- Subconcepts.
- Prerequisites.
- Relationships.
- Difficulty estimates.
- Which concepts require examples.
- Which concepts are suitable for visual animation.
- Which concepts can be omitted without damaging understanding.

**Consumer:** Lesson planner and content generation agents.

---

# 10. Stage 2 — Pedagogical Planning Agents

### 10.1 Lesson / Chapter Planner

**Purpose:** Decide the instructional sequence.

**Input:** Intent Analysis + Learning Requirements + Concept Map.

**Output:** `LessonPlan` containing ordered chapters/scenes, chapter objectives, prerequisites, estimated durations, and dependencies.

**Consumer:** Learning Objective Agent, content agents, visual planner.

**Key requirement:** The plan should be teachable, not simply a list of facts.

---

### 10.2 Learning Objective Agent

**Purpose:** Turn the lesson plan into measurable learning outcomes.

**Input:** Lesson Plan + Requirements.

**Output:** `LearningObjectives` containing objectives such as:

- Explain a concept.
- Trace an algorithm.
- Implement a procedure.
- Compare alternatives.
- Predict behavior.
- Identify complexity.

**Consumer:** Content validators and final content generation.

**Why it matters:** These objectives become an evaluation reference. A generated lesson should satisfy its objectives instead of merely being fluent.

---

### 10.3 Example & Exercise Planner

**Purpose:** Decide which examples, counterexamples, edge cases, and exercises are required.

**Input:** Lesson Plan + Learning Objectives + Concept Map.

**Output:** `ExamplePlan` containing:

- Example descriptions.
- Input data.
- Expected result.
- Edge cases.
- Demonstration sequence.
- Difficulty progression.

**Consumer:** Worked Example Agent, Execution Trace Agent, and Visual Planner.

---

# 11. Stage 3 — Educational Content Agents

### 11.1 Concept Explanation Agent

**Purpose:** Write clear teaching material for conceptual sections.

**Input:** Lesson Plan + Learning Objectives + Concept Map + Requirements.

**Output:** `ExplanationArtifact` containing structured sections rather than one giant text blob.

Each section should contain:

- Concept.
- Explanation.
- Intuition.
- Important terminology.
- Common misconception.
- Required visual idea.
- Transition to the next concept.

**Consumer:** Narration Agent, Visual Planner, Content Validator.

---

### 11.2 Algorithm / Procedure Agent

**Purpose:** Produce rigorous step-by-step procedures for algorithmic or procedural topics.

**Input:** Relevant concept map + lesson plan + requirements.

**Output:** `ProcedureArtifact` containing:

- Preconditions.
- Inputs.
- Ordered steps.
- State transitions.
- Termination condition.
- Complexity.
- Correctness intuition.
- Edge cases.

**Consumer:** Worked Example Agent, Execution Trace Agent, Visual Planner, Content Validator.

---

### 11.3 Worked Example Agent

**Purpose:** Turn abstract material into a concrete example that can be followed visually.

**Input:** Explanation/Procedure + Example Plan.

**Output:** `WorkedExampleArtifact` containing the example input, expected output, intermediate states, and explanation of each state transition.

**Consumer:** Execution Trace Agent, Visual Planner, Narration Agent.

---

### 11.4 Execution Trace Agent

**Purpose:** Produce machine-checkable intermediate states for algorithms/program execution.

**Input:** Procedure + Worked Example.

**Output:** `ExecutionTrace` containing ordered states and transitions.

**Consumer:** Visual Planner and potentially a deterministic simulator.

**Important:** For programming topics, prefer executing or simulating simple examples with deterministic tooling where feasible instead of trusting an LLM-generated trace blindly.

---

# 12. Stage 4 — Visual Planning Agents

### 12.1 Visual Planner Agent

**Purpose:** Decide how each educational concept should be represented visually.

**Input:** Educational Content Artifact + Learning Objectives + Requirements.

**Output:** `VisualPlan` containing:

- Concept-to-visual mapping.
- Visual type.
- Objects/entities.
- Transformations.
- Labels.
- Highlights.
- Transitions.
- Required diagrams.
- Whether Manim is suitable.

**Consumer:** Scene Planner, Code Visualization Planner, Timing Planner.

**Examples:**

- Arrays → boxes with indices.
- Binary search → search interval shrinking.
- Recursion → call stack expansion/collapse.
- Gradient descent → point moving down a curve.
- Linked list → nodes and arrows.

---

### 12.2 Scene / Manim Planner

**Purpose:** Translate the visual plan into a concrete scene storyboard without writing full implementation code.

**Input:** Visual Plan + Lesson Plan + Timing constraints.

**Output:** `Storyboard` containing ordered scenes.

Each scene should define:

- Scene identifier.
- Purpose.
- Input state.
- Objects.
- Initial layout.
- Animation operations.
- Text/labels.
- Narration anchor.
- Expected duration.
- Exit state.

**Consumer:** Manim Code Generator and Timing system.

---

### 12.3 Code Visualization Planner

**Purpose:** Handle programming-specific visuals such as syntax highlighting, line highlighting, variable changes, stack frames, data structures, and execution pointers.

**Input:** Procedure + Execution Trace + Storyboard.

**Output:** `CodeVisualPlan` containing:

- Code representation.
- Highlight sequence.
- Variable-state changes.
- Pointer/index movement.
- Execution markers.
- Mapping between code lines and narration/visual events.

**Consumer:** Manim Code Generator.

---

### 12.4 Timing Planner

**Purpose:** Establish a common temporal coordinate system for video, narration, and captions.

**Input:** Storyboard + narration requirements.

**Output:** `TimingPlan` containing:

- Scene start/end targets.
- Event anchors.
- Narration segments.
- Caption segments.
- Transition durations.
- Tolerance thresholds.

**Consumer:** Narration Agent, Subtitle Processor, Sync Validator, media composer.

**Important:** Timing should not be treated as an afterthought. It is a first-class artifact shared by visual and audio generation.

---

# 13. Stage 5 — Generation Agents

### 13.1 Manim Code Generator Agent

**Purpose:** Convert the storyboard into executable Manim code.

**Input:** Storyboard + Code Visual Plan + project rendering constraints.

**Output:** `ManimArtifact` containing:

- Source code.
- Scene identifiers.
- Required dependencies.
- Expected output paths.
- Code version.

**Consumer:** Schema validator, static validator, render smoke test, Manim renderer.

**Requirements:**

- Generated code must follow a restricted execution policy.
- The generator should use reusable project primitives/templates where possible.
- The agent should not freely invent external dependencies.
- Code should be deterministic when given the same artifact and configuration.

---

### 13.2 Narration Agent

**Purpose:** Generate the spoken teaching script.

**Input:** Educational Content + Storyboard + Timing Plan + Requirements.

**Output:** `NarrationArtifact` containing:

- Segment identifier.
- Spoken text.
- Target start/end time.
- Scene association.
- Pronunciation hints where required.
- Delivery style.

**Consumer:** TTS Engine, Sync Validator, Subtitle Generator.

**Key requirement:** Narration should describe what the learner needs to understand, not simply read every visible label aloud.

---

### 13.3 Subtitle / Caption Planner

**Purpose:** Produce caption segments aligned to narration and timing.

**Input:** Narration Artifact + Timing Plan.

**Output:** `SubtitleArtifact` containing ordered caption segments with timestamps.

**Consumer:** Subtitle Processor and Sync Validator.

---

# 14. Stage 6 — Validation

Validation should be implemented as quality gates. Not every validator needs to be an LLM.

### 14.1 Schema / Contract Validator

Checks that every artifact matches its expected structure.

**Input:** Any stage artifact.

**Output:** pass/fail + validation errors.

**Recovery:** Return to the producer of the invalid artifact.

---

### 14.2 Python / Manim Static Validator

Checks generated code before rendering.

Checks should include:

- Python syntax.
- Required scene definitions.
- Forbidden operations.
- Missing imports.
- Invalid project APIs.
- Obvious infinite loops or unsafe constructs where detectable.

**Recovery:** Manim Code Generator or Code Repair Agent.

---

### 14.3 Render Smoke Test

Runs a lightweight render for each generated scene or a representative subset.

**Input:** Validated Manim Artifact.

**Output:** Render success/failure + logs + generated preview artifact.

**Recovery:** Code Repair Agent followed by regeneration.

---

### 14.4 Educational Correctness Validator

Checks whether the generated lesson satisfies its learning objectives and is logically/factually coherent.

This can use a combination of deterministic checks and an LLM judge.

**Input:** Learning Objectives + Educational Content + Procedure + Examples.

**Output:** Validation report with:

- Objective coverage.
- Contradictions.
- Missing explanations.
- Suspected factual errors.
- Example consistency.
- Confidence/severity.

**Recovery:** Content refinement loop.

---

### 14.5 Audio / Visual Synchronization Validator

Checks whether:

- Narration exists for required scenes.
- Caption timestamps are valid.
- Scene timing and audio duration are compatible.
- No caption starts before the associated scene.
- No important visual event occurs without an intended narration anchor.

**Recovery:** Timing correction, narration revision, or storyboard adjustment.

---

# 15. Recovery and Refinement

The original diagram's recovery concept is good, but recovery should be targeted.

### 15.1 Code Repair Agent

Triggered by:

- Syntax failure.
- Static validation failure.
- Manim render failure.
.

**Input:** Original Manim Artifact + validator/render error + Storyboard.

**Output:** Corrected Manim Artifact.

The repair agent must not rewrite educational content unless the error proves that the storyboard itself is impossible.

### 15.2 Content Refinement Agent

Triggered by educational correctness failures.

**Input:** Failed content artifact + validation report.

**Output:** Corrected educational content.

### 15.3 Timing Correction

Prefer a planning or deterministic timing service rather than an LLM agent where possible.

**Input:** Timing Plan + measured audio/video durations.

**Output:** Revised timing anchors.

Only regenerate affected narration/captions/scenes.

---

# 16. Shared Workflow State

LangGraph state should contain references to typed artifacts and workflow metadata.

Recommended state categories:

### Request

- Job ID.
- User request.
- Request hash.
- User preferences.

### Understanding

- Intent Analysis.
- Learning Requirements.
- Concept Map.

### Planning

- Lesson Plan.
- Learning Objectives.
- Example Plan.

### Content

- Explanation Artifact.
- Procedure Artifact.
- Worked Examples.
- Execution Traces.

### Visual

- Visual Plan.
- Storyboard.
- Code Visual Plan.
- Timing Plan.

### Generation

- Manim Artifact.
- Narration Artifact.
- Subtitle Artifact.

### Validation

- Validation reports.
- Current quality status.
- Failure reason.
- Retry counters.

### Assets

- Rendered video references.
- Audio reference.
- Subtitle reference.
- Thumbnail reference.
- Final metadata.

### Workflow control

- Current stage.
- Previous stage.
- Revision target.
- Attempt number.
- Overall status.

Do not store arbitrary LLM conversations as the primary state model. Store durable, structured artifacts and relevant diagnostics.

---

# 17. Artifact Contract Strategy

The most important implementation improvement after the current Intent Analyzer is to create schemas for artifacts before creating additional agents.

Recommended artifact sequence:

1. `IntentAnalysis`
2. `LearningRequirements`
3. `ConceptMap`
4. `LessonPlan`
5. `LearningObjectives`
6. `ExamplePlan`
7. `ExplanationArtifact`
8. `ProcedureArtifact`
9. `WorkedExampleArtifact`
10. `ExecutionTrace`
11. `VisualPlan`
12. `Storyboard`
13. `CodeVisualPlan`
14. `TimingPlan`
15. `ManimArtifact`
16. `NarrationArtifact`
17. `SubtitleArtifact`
18. `ValidationReport`
19. `FinalVideoArtifact`

This sequence gives the project a backbone. Agents become producers/consumers of these artifacts rather than passing uncontrolled strings between one another.

---

# 18. Agent Dependency Matrix

| Producer | Output | Primary Consumer |
|---|---|---|
| Intent Analyzer | Intent Analysis | Scope Agent |
| Scope Agent | Learning Requirements | Concept Mapper |
| Concept Mapper | Concept Map | Lesson Planner |
| Lesson Planner | Lesson Plan | Objective Agent + Content Agents |
| Objective Agent | Learning Objectives | Content Validator |
| Example Planner | Example Plan | Worked Example Agent |
| Explanation Agent | Explanation Artifact | Narration + Visual Planner |
| Algorithm Agent | Procedure Artifact | Example + Trace + Visual |
| Worked Example Agent | Worked Example | Trace + Visual |
| Trace Agent | Execution Trace | Visual Planner |
| Visual Planner | Visual Plan | Scene Planner |
| Scene Planner | Storyboard | Manim Generator |
| Code Visual Planner | Code Visual Plan | Manim Generator |
| Timing Planner | Timing Plan | Narration + Subtitle + Sync |
| Manim Generator | Manim Artifact | Validators + Renderer |
| Narration Agent | Narration Artifact | TTS + Sync + Subtitle |
| Subtitle Planner | Subtitle Artifact | Caption Processor + Sync |
| Validators | Validation Reports | Workflow Router |
| Code Repair Agent | Revised Manim Artifact | Validators |
| Content Refinement Agent | Revised Content | Content Validator |
| Renderer | Rendered Video | Media Composer |
| TTS Engine | Audio | Media Composer |
| Media Composer | Base Video | Caption Processor |
| Caption Processor | Final Video | Thumbnail Generator |
| Thumbnail Generator | Final Assets | Delivery API |

---

# 19. Orchestration Rules

The LangGraph workflow should implement explicit states and transitions.

### Rule 1 — Every stage has a completion condition

The workflow must know what artifact indicates completion.

### Rule 2 — Every failure has a destination

A failure should not result in an unbounded loop.

### Rule 3 — Retries are bounded

Each stage should have a maximum retry count.

### Rule 4 — Revision is targeted

A rendering error should not cause intent analysis to run again.

### Rule 5 — Artifact versions matter

When an artifact is regenerated, increment its version or assign a new artifact ID.

### Rule 6 — The workflow is resumable

A completed stage should not be repeated simply because a later stage failed.

### Rule 7 — The workflow must terminate

Possible terminal states should include:

- Completed.
- Failed permanently.
- Cancelled.
- Waiting for user clarification.

---

# 20. Example End-to-End Scenario

Request:

> Teach me binary search in Java to a beginner. Show me a visual example and explain complexity.

### Step 1 — Intent Analyzer

Produces:

- Domain: computer science.
- Topic: binary search.
- Audience: beginner.
- Language: Java.
- Desired deliverable: visual explanation + complexity.

### Step 2 — Scope

Determines that the lesson should explain sorted arrays, search interval, midpoint, comparison, interval reduction, termination, implementation, and complexity.

### Step 3 — Concept Mapper

Creates dependencies:

Sorted array → search interval → midpoint → comparison → interval reduction → termination → implementation → complexity.

### Step 4 — Lesson Planner

Creates chapters:

1. What problem binary search solves.
2. Why sorting matters.
3. Visual intuition.
4. Worked example.
5. Java implementation.
6. Complexity.
7. Common mistakes.

### Step 5 — Content Agents

Generate explanations, algorithm steps, a concrete array, and an execution trace.

### Step 6 — Visual Planner

Chooses an array of boxes and a shrinking search interval.

### Step 7 — Scene Planner

Defines scenes for:

- Array introduction.
- Initial interval.
- Midpoint selection.
- Comparison.
- Eliminating half.
- Repeating.
- Result.
- Complexity summary.

### Step 8 — Manim Generator

Generates the implementation from the storyboard.

### Step 9 — Narration

Generates speech synchronized to scene events.

### Step 10 — Validation

Checks content, code, render, and timing.

### Step 11 — Rendering

Manim produces the visual video; TTS produces narration; FFmpeg combines them; captions are attached.

### Step 12 — Delivery

The user receives the final explainer and metadata.

---

# 21. Quality Requirements

## 21.1 Correctness

Generated educational content should be factually and logically consistent.

## 21.2 Reproducibility

Given identical input artifacts, model configuration, and deterministic tools, output should be as reproducible as practical.

## 21.3 Reliability

Transient provider failures should not destroy the complete job.

## 21.4 Observability

Every stage should expose:

- Job ID.
- Stage name.
- Agent name.
- Attempt number.
- Start/end time.
- Model/provider.
- Input artifact IDs.
- Output artifact IDs.
- Token/cost information when available.
- Validation result.
- Failure reason.

## 21.5 Security

Generated code must execute in a constrained environment. The system must not allow arbitrary generated code to access sensitive host resources.

API keys must remain outside source-controlled files and must never be written into artifacts or logs.

## 21.6 Performance

The system should avoid regenerating unchanged artifacts. Rendering and other expensive operations should run asynchronously for production usage.

## 21.7 Maintainability

Agents should be independently testable and provider-independent.

---

# 22. Testing Strategy

### Unit tests

Every agent should have tests for:

- Valid input.
- Invalid input.
- Valid output.
- Malformed model output.
- Provider failure.
- Retry behavior.
- Boundary cases.

### Contract tests

Verify that the output schema of each producer is accepted by its consumers.

### Integration tests

Run a multi-stage workflow with mocked LLMs and deterministic fake renderers.

### Rendering tests

Run representative Manim scenes and verify successful output.

### End-to-end tests

Use a small educational request and verify that a final asset is produced.

### Regression tests

Maintain a collection of representative educational prompts and expected structural properties.

---

# 23. Prompt Engineering Requirements

Each agent prompt should define:

1. Role.
2. Exact task.
3. Input artifact semantics.
4. Output schema.
5. Quality rules.
6. Forbidden behavior.
7. Examples where useful.
8. Instructions for uncertainty.

Prompts should not be responsible for workflow control. Routing, retries, and state transitions belong to the orchestration layer.

The current Intent Analyzer prompt is directionally correct but should eventually be made more explicit and grammatically precise, and its output requirements should align exactly with the schema.

---

# 24. LLM Provider Strategy

The current provider abstraction should be preserved.

Supported providers may include:

- Gemini.
- Groq.
- OpenAI.

The provider layer should expose a consistent interface to agents.

Provider-specific behavior such as authentication, model selection, retries, rate limits, and key rotation should remain below the agent business-logic layer.

Agents should not contain provider-specific branching unless unavoidable.

---

# 25. Storage Strategy

### Redis

Use for:

- Cache lookup.
- Short-lived job status.
- Rate limiting.
- Potential queue coordination.

### MySQL

Use for durable metadata:

- Users.
- Jobs.
- Workflow status.
- Artifact metadata.
- Model/provider information.
- Job history.
- Final asset references.

### Object storage

Use for large binary assets:

- MP4.
- Audio.
- Images.
- Captions.
- Render previews.

Do not store large videos directly inside the relational database.

---

# 26. API-Level Requirements

The eventual API should conceptually support:

### Create job

Input:

- User prompt.
- Optional audience.
- Optional language.
- Optional duration.
- Optional output preferences.

Output:

- Job ID.
- Initial status.

### Get job status

Returns:

- Job ID.
- Current stage.
- Percentage/phase progress.
- Current status.
- Error information if applicable.

### Get result

Returns:

- Video URL.
- Thumbnail URL.
- Duration.
- Captions.
- Topic metadata.
- Generation metadata.

### Regenerate

Accepts a revision request and identifies which part should change where possible.

---

# 27. Recommended Repository Evolution

The current repository should evolve toward a structure conceptually similar to:

- `agents/` — bounded reasoning/generation agents.
- `schemas/` — all artifact contracts.
- `prompts/` — versioned agent prompts.
- `graph/` — LangGraph workflow definitions and routing.
- `services/` — deterministic application services.
- `tools/` — Manim, TTS, FFmpeg, validators, and execution wrappers.
- `storage/` — persistence and artifact repositories.
- `tests/` — unit, contract, integration, and end-to-end tests.
- `docs/` — SRS, architecture, execution, testing, and agent specifications.

Do not restructure everything immediately. Introduce this architecture incrementally.

---

# 28. Implementation Roadmap

## Phase 0 — Stabilize current agent

1. Keep Intent Analyzer as the first production-quality component.
2. Improve its prompt.
3. Strengthen its schema using controlled enums where useful.
4. Add more unit tests.
5. Add structured error types.
6. Add logging/observability.

**Exit criterion:** Intent Analyzer reliably converts diverse educational requests into valid structured intent.

## Phase 1 — Build contracts before agents

Implement schemas for:

- Learning Requirements.
- Concept Map.
- Lesson Plan.
- Learning Objectives.
- Example Plan.

**Exit criterion:** The first planning pipeline can run using mocked agents.

## Phase 2 — Build the planning graph

Implement:

Intent → Scope → Concept Map → Lesson Plan → Objectives/Examples.

Do not generate video yet.

**Exit criterion:** A request produces a complete validated lesson plan.

## Phase 3 — Build educational content

Implement explanation, procedure, example, and trace generation.

Add content validation.

**Exit criterion:** A lesson plan produces a validated educational content package.

## Phase 4 — Build visual planning

Implement Visual Plan, Storyboard, Code Visual Plan, and Timing Plan.

**Exit criterion:** The system can describe the complete video without writing/rendering code.

## Phase 5 — Build Manim generation

Implement Manim generator + static validation + smoke rendering + repair loop.

**Exit criterion:** Representative programming/math topics produce renderable scenes.

## Phase 6 — Add narration and captions

Implement narration, TTS integration, subtitle generation, and timing validation.

**Exit criterion:** Audio and visuals are synchronized for representative examples.

## Phase 7 — Media pipeline

Integrate FFmpeg, captions, thumbnails, object storage, and delivery.

**Exit criterion:** One end-to-end request produces a final playable explainer.

## Phase 8 — Production hardening

Add:

- Persistent checkpoints.
- Queues/background workers.
- Rate limiting.
- Authentication.
- Observability.
- Cost tracking.
- Caching.
- Cancellation.
- Retry policies.

---

# 29. What Should NOT Be Built Yet

To prevent scope explosion, do not immediately implement all of these as separate agents:

- Separate agent for every tiny educational task.
- Separate LLM safety agent for ordinary static checks.
- Multiple competing planners.
- Autonomous web research.
- Complex long-term learner memory.
- Fully automatic arbitrary code execution.
- Advanced personalization.
- Multiple video rendering backends.

First prove this path:

**Intent → Plan → Content → Visual Plan → Manim → Validate → Render**

Then add audio synchronization.

---

# 30. Critical Improvements to the Original Architecture

### Improvement 1 — Reduce agent count

The original conceptual diagram contains many boxes that could become unnecessary LLM calls. Combining closely related responsibilities reduces latency, cost, and failure surface.

### Improvement 2 — Make artifacts first-class

The old architecture primarily connected agents directly. The target architecture connects agents through explicit artifacts and shared workflow state.

### Improvement 3 — Separate planning from execution

Agents should decide what should happen. Deterministic tools should perform the actual rendering/composition.

### Improvement 4 — Introduce validation gates before expensive operations

Do not render obviously invalid Python. Do not synthesize narration for content that has failed basic validation.

### Improvement 5 — Use targeted repair loops

A single failure should not restart the whole pipeline.

### Improvement 6 — Treat timing as an architectural concern

Audio, animation, and captions need a common timeline artifact.

### Improvement 7 — Make generated code a controlled artifact

Manim generation must be constrained, statically checked, and executed in a sandboxed environment.

### Improvement 8 — Make the graph the brain of the workflow

Agents should not call arbitrary downstream agents themselves. LangGraph should determine which node runs next.

---

# 31. Definition of Done for the First Complete Version

A first complete Didactics release should satisfy all of the following:

1. User submits a natural-language educational request.
2. Intent is converted into validated structured data.
3. A lesson plan is generated.
4. Learning objectives are explicit.
5. Educational content is generated and validated.
6. A visual storyboard is generated.
7. Manim code is generated from the storyboard.
8. Generated code passes static validation.
9. A render smoke test succeeds.
10. Narration is generated.
11. TTS produces audio.
12. Captions are generated.
13. Synchronization is validated.
14. FFmpeg creates the final video.
15. The final asset is stored.
16. The API returns a playable result.
17. Failures are visible and recoverable.
18. At least one targeted repair loop works.
19. Intermediate artifacts are testable independently.
20. The complete workflow can be executed with mocked LLMs in tests.

---

# 32. Final Architectural Mental Model

Think about Didactics as a **compiler for educational videos**.

The analogy is useful:

- User prompt = source language.
- Intent Analysis = parsing.
- Concept Map = semantic analysis.
- Lesson Plan = intermediate representation.
- Educational Content = semantic/teaching representation.
- Storyboard = visual intermediate representation.
- Manim code = target program.
- Validators = compiler checks.
- Manim = execution/rendering backend.
- Narration/TTS = audio backend.
- FFmpeg = linker/media composer.
- Final MP4 = compiled artifact.

This mental model is preferable to thinking of Didactics as "a bunch of agents talking to each other."

The agents are specialized transformations. The workflow is the compiler pipeline. The artifacts are the intermediate representations. The validators are quality gates. The deterministic tools execute the final plan.

That architecture will scale much better than adding agents ad hoc.
