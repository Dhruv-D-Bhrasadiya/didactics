# Didactics — Focused MVP Architecture

## Product boundary

The first milestone supports one entry point: a **LeetCode problem number**. It looks up the canonical problem, displays the retrieved details, and lets the learner select one of two paths: solve the problem or learn its prerequisites.

```mermaid
flowchart TB
    U([Learner]) --> UI[Client UI]
    UI -->|Problem number| API[FastAPI API]
    API --> V[Input validation]
    V -->|Valid number| Lookup[Problem Lookup Service]
    V -->|Invalid input| Error[Validation response]
    Lookup --> Adapter[LeetCode Source Adapter]
    Adapter --> Source[(LeetCode problem source)]
    Source --> Normalize[Normalize + validate metadata]
    Normalize --> Cache[(Problem metadata cache)]
    Cache --> Summary[Problem Details Response]
    Summary --> UI
    UI --> Choice{Learner selects intent}

    Choice -->|Solve| SolveReq[Solution-path request]
    Choice -->|Prerequisites| PrereqReq[Prerequisite-path request]

    SolveReq --> Router[Learning Path Router]
    PrereqReq --> Router
    Router --> Context[Problem context + learner preferences]
    Context --> SolveAgent[Solution Teaching Generator]
    Context --> PrereqAgent[Prerequisite Curriculum Generator]

    SolveAgent --> SolveSchema[SolutionLearningPlan validation]
    PrereqAgent --> PrereqSchema[PrerequisiteLearningPath validation]
    SolveSchema -->|Valid| Session[Learning Session response]
    PrereqSchema -->|Valid| Session
    Session --> UI
    Error --> UI

    subgraph LLM[Configured LLM Provider Layer]
      Models[Gemini / Groq / OpenAI adapters]
    end
    SolveAgent -.-> Models
    PrereqAgent -.-> Models

    subgraph Reliability[Cross-cutting controls]
      Timeout[Timeouts + bounded retries]
      Provenance[Source URL + retrieval metadata]
      Tests[Unit + contract + end-to-end tests]
    end
    Adapter -.-> Timeout
    Normalize -.-> Provenance
    SolveSchema -.-> Tests
    PrereqSchema -.-> Tests
```

## Request sequence

```mermaid
sequenceDiagram
    actor Learner
    participant UI as Client
    participant API as FastAPI
    participant Lookup as Problem Lookup
    participant LC as LeetCode Source
    participant LLM as Teaching Generator

    Learner->>UI: Enter problem number
    UI->>API: GET /api/problems/{number}
    API->>Lookup: Validate + lookup
    Lookup->>LC: Fetch canonical problem
    LC-->>Lookup: Statement, examples, constraints, tags
    Lookup-->>API: ProblemDetails + source provenance
    API-->>UI: Render problem summary
    Learner->>UI: Select Solve or Prerequisites
    UI->>API: POST /api/learning-paths
    API->>LLM: Generate only the selected path
    LLM-->>API: Structured learning artifact
    API->>API: Pydantic validation
    API-->>UI: Learning session
```

## Responsibilities

| Component | Responsibility | Must not do |
|---|---|---|
| Client | Collect number, show fetched problem, collect intent | Guess metadata |
| Problem Lookup Service | Validate number, call adapter, normalize source fields | Ask an LLM to invent question content |
| LeetCode Source Adapter | Encapsulate upstream request and source-specific parsing | Contain teaching prompts |
| Learning Path Router | Route to exactly one selected learning mode | Run both modes by default |
| Solution Teaching Generator | Explain strategy, trace, correctness, complexity, implementation | Change canonical problem facts |
| Prerequisite Curriculum Generator | Identify and teach relevant concepts in dependency order | Reveal full solution by default |
| Schema Validators | Reject incomplete or malformed artifacts | Silently coerce invalid content |
| Cache | Reuse source metadata safely | Serve stale/unattributed problem details |

## Learning path contracts

### Solve path

```mermaid
flowchart LR
    P[Confirmed Problem] --> T[Task and constraints]
    T --> O[Key observations]
    O --> A[Approach derivation]
    A --> W[Worked example / trace]
    W --> C[Correctness rationale]
    C --> X[Time and space complexity]
    X --> I[Implementation in selected language]
```

### Prerequisites path

```mermaid
flowchart LR
    P[Confirmed Problem] --> R[Identify required concepts]
    R --> D[Build dependency graph]
    D --> O[Topological learning order]
    O --> E[Explain each concept]
    E --> Q[Example + knowledge check]
    Q --> B[Connect concepts to target problem]
```

## Error handling

- Invalid number: return a validation error and keep the number field editable.
- Problem not found: return a not-found result; do not call the teaching model.
- Source unavailable/rate-limited: return a retriable upstream error; do not fabricate a problem.
- Missing optional metadata: label it unavailable and continue only if required problem context exists.
- LLM timeout/provider failure: return a recoverable generation error and preserve the confirmed problem.
- Invalid generated schema: reject it; allow bounded repair/retry, then surface a clear error.
- Unknown/unsupported intent: reject it rather than selecting a mode implicitly.

## Scope guard

The following are intentionally outside the first milestone: generic topic prompting, multi-platform ingestion, Manim/video/TTS generation, autonomous code submission, progress dashboards, social features, and a large multi-agent graph. Add these only after the problem-number-to-learning-path journey works reliably end to end.
