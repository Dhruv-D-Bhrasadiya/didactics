# Didactics — System, Learning and Animation Architecture

## 1. Product overview

Didactics accepts a LeetCode problem number, retrieves the canonical problem, and asks the learner to configure:
- Programming language: **Java, Python, C, C++**
- DSA proficiency: **Beginner, Intermediate, Advanced**
- Programming proficiency: **Beginner, Intermediate, Advanced**

The learner then chooses **Solve this problem** or **Teach me the prerequisites**. Both paths produce level-aware learning content. The solve path also produces language-specific code and a shared algorithm trace. The animation pipeline converts that trace into a storyboard, renders it, validates the output, and attaches it to the learning session.

## 2. End-to-end user journey

```mermaid
flowchart TD
    U([Learner]) --> N[Enter LeetCode problem number]
    N --> V[Validate number]
    V --> L[Fetch problem from LeetCode source adapter]
    L --> P[Normalize and validate ProblemDetails]
    P --> C{Problem found?}
    C -->|No| E[Show not-found / unavailable state]
    E --> N
    C -->|Yes| D[Display title, statement, examples, constraints, difficulty and tags]
    D --> LANG[Select language: Java / Python / C / C++]
    LANG --> DSA[Select DSA proficiency]
    DSA --> DSA2[Beginner / Intermediate / Advanced]
    DSA2 --> PROG[Select programming proficiency]
    PROG --> PROG2[Beginner / Intermediate / Advanced]
    PROG2 --> INTENT{Choose learning intent}
    INTENT -->|Solve| SOLVE[Solution teaching workflow]
    INTENT -->|Prerequisites| PREREQ[Prerequisite curriculum workflow]
    SOLVE --> CODE[Generate selected-language code + syntax support]
    PREREQ --> CONCEPTS[Generate ordered concept lessons + checks]
    CODE --> TRACE[Create canonical algorithm trace]
    CONCEPTS --> CTRACE[Create concept examples / optional visual traces]
    TRACE --> ANIM[Animation generation pipeline]
    CTRACE --> ANIM
    ANIM --> SESSION[Assemble learning session]
    CODE --> SESSION
    CONCEPTS --> SESSION
    SESSION --> PLAYER[Lesson UI + animation player]
```

## 3. System architecture

```mermaid
flowchart TB
    subgraph CLIENT[Client Application]
      UI[Problem number input]
      DETAILS[Problem details review]
      SETTINGS[Language + DSA level + programming level]
      PATH[Intent selection]
      LESSON[Lesson renderer]
      PLAYER[Animation player: play / pause / step / replay]
      UI --> DETAILS --> SETTINGS --> PATH
      LESSON --> PLAYER
    end

    subgraph API[Application API]
      PROBLEMAPI[Problem lookup endpoint]
      SESSIONAPI[Learning session endpoint]
      VALIDATE[Request and schema validation]
      ROUTER[Learning intent router]
      CONFIG[Learner configuration object]
    end

    subgraph DATA[Canonical Problem Data]
      ADAPTER[LeetCode source adapter]
      NORMALIZE[Normalize source payload]
      CACHE[(Problem metadata cache)]
      ADAPTER --> NORMALIZE --> CACHE
    end

    subgraph TEACH[Teaching and Personalization]
      CONTEXT[Problem + learner context]
      SOLVE[Solution teaching generator]
      PREREQ[Prerequisite curriculum generator]
      CODEX[Language-specific code generator]
      SYNTAX[Syntax annotation generator]
      TRACE[Canonical algorithm trace builder]
      DEP[Concept dependency planner]
    end

    subgraph ANIMATION[Animation Generation Service]
      STORY[Typed storyboard planner]
      SCENE[Scene and state builder]
      RENDER[Renderer adapter: Manim first]
      QA[Render and visual QA]
      STORE[(Storyboard + video artifact store)]
      JOB[Async render job / worker]
      STORY --> SCENE --> JOB --> RENDER --> QA
      QA -->|Pass| STORE
      QA -->|Fail: bounded retry| STORY
    end

    UI --> PROBLEMAPI
    PROBLEMAPI --> VALIDATE --> ADAPTER
    CACHE --> PROBLEMAPI --> DETAILS
    SETTINGS --> CONFIG
    PATH --> SESSIONAPI --> VALIDATE --> ROUTER
    CONFIG --> CONTEXT
    CACHE --> CONTEXT
    ROUTER -->|solve| SOLVE
    ROUTER -->|prerequisites| PREREQ
    CONTEXT --> SOLVE
    CONTEXT --> PREREQ
    SOLVE --> CODEX
    CODEX --> SYNTAX
    CODEX --> TRACE
    PREREQ --> DEP
    DEP --> TRACE
    TRACE --> STORY
    STORY --> STORE
    SOLVE --> LESSON
    PREREQ --> LESSON
    CODEX --> LESSON
    SYNTAX --> LESSON
    STORE --> PLAYER
    SESSIONAPI --> LESSON
```

## 4. Learner configuration and personalization

```mermaid
flowchart LR
    A[Learner settings] --> B[Language]
    A --> C[DSA proficiency]
    A --> D[Programming proficiency]
    B --> E[Language adapter]
    C --> F[Algorithm depth policy]
    D --> G[Syntax explanation policy]
    E --> H[Personalized lesson context]
    F --> H
    G --> H
    H --> I[Selected learning path]
```

| Setting | Values | Output behavior |
|---|---|---|
| Language | Java / Python / C / C++ | All code, syntax notes and language-specific examples use the chosen language |
| DSA proficiency | Beginner / Intermediate / Advanced | Controls prerequisite depth, terminology, derivation detail and complexity discussion |
| Programming proficiency | Beginner / Intermediate / Advanced | Controls explanation of language constructs, syntax and standard-library APIs |

### Programming proficiency policy

- **Beginner:** Explain the actual code line by line where useful. Define syntax used in the solution: declarations, types, assignments, loops, conditionals, methods/functions, arrays/collections, pointers/references, memory concepts and library calls as applicable. Include a small syntax example before the full code when a construct is unfamiliar.
- **Intermediate:** Explain non-obvious syntax, APIs, data representation and language-specific trade-offs. Do not explain basic assignment/loop syntax unless relevant.
- **Advanced:** Provide concise idiomatic code, highlight subtle language behavior and focus on algorithmic decisions/performance.

DSA and programming proficiency are independent axes. Never infer one from the other.

## 5. Learning intent workflows

### 5.1 Solve path

```mermaid
flowchart TD
    A[Confirmed problem + learner config] --> B[Parse task, inputs, outputs and constraints]
    B --> C[Identify observations]
    C --> D[Explain brute force baseline if useful]
    D --> E[Derive optimized approach]
    E --> F[Explain correctness]
    F --> G[Analyze time and space complexity]
    G --> H[Generate code in selected language]
    H --> I{Programming level?}
    I -->|Beginner| J[Add syntax primer + annotated code]
    I -->|Intermediate| K[Explain non-obvious syntax and APIs]
    I -->|Advanced| M[Idiomatic concise implementation]
    J --> T[Build canonical trace]
    K --> T
    M --> T
    T --> W[Worked example and edge-case walkthrough]
    W --> X[Lesson artifact]
```

### 5.2 Prerequisite path

```mermaid
flowchart TD
    A[Confirmed problem + learner config] --> B[Identify concepts required]
    B --> C[Build prerequisite dependency graph]
    C --> D[Topologically order concepts]
    D --> E[Adapt concept depth to DSA proficiency]
    E --> F[Create concept explanation + standalone example]
    F --> G[Adapt example syntax to programming proficiency and language]
    G --> H[Knowledge check]
    H --> I{More concepts?}
    I -->|Yes| F
    I -->|No| J[Connect prerequisites to target problem]
    J --> K[Do not reveal full solution by default]
    K --> L[Prerequisite lesson artifact]
```

## 6. Main animation generation architecture

Animation generation is a separate pipeline consuming validated lesson data and a canonical trace. The LLM may propose a storyboard in a strict schema; deterministic code validates and renders it. Do not let the model submit arbitrary shell commands or unrestricted Python for execution.

```mermaid
flowchart TD
    A[Solution trace or prerequisite concept trace] --> B[Animation planning prompt + render profile]
    B --> C[Storyboard JSON]
    C --> D{Storyboard schema valid?}
    D -->|No| E[Schema error feedback / bounded repair]
    E --> C
    D -->|Yes| F[Semantic validation]
    F --> G{States and transitions consistent?}
    G -->|No| E
    G -->|Yes| H[Scene decomposition]
    H --> I[Map data structures to visual primitives]
    I --> J[Generate renderer instructions from trusted templates]
    J --> K[Queue isolated render job]
    K --> L[Manim renderer adapter]
    L --> M[Frames and video output]
    M --> N[Automated QA]
    N --> O{Render acceptable?}
    O -->|No| P[Capture error diagnostics]
    P --> Q{Retry budget remains?}
    Q -->|Yes| H
    Q -->|No| R[Mark animation unavailable; retain text lesson]
    O -->|Yes| S[Persist video + storyboard + metadata]
    S --> T[Attach to lesson timeline]
    R --> U([Learning session ready])
    T --> U
```

### Animation data flow and contracts

```mermaid
sequenceDiagram
    participant Teach as Teaching Generator
    participant Trace as Trace Builder
    participant Planner as Storyboard Planner
    participant Validator as Storyboard Validator
    participant Queue as Render Queue
    participant Worker as Isolated Worker
    participant Manim as Manim Adapter
    participant QA as Render QA
    participant Store as Artifact Store
    participant UI as Lesson Player

    Teach->>Trace: Structured algorithm / concept states
    Trace->>Planner: Canonical trace + learner profile
    Planner->>Validator: Storyboard JSON
    Validator-->>Planner: Validated storyboard or errors
    Planner->>Queue: Enqueue render job
    Queue->>Worker: Job ID + storyboard reference
    Worker->>Manim: Trusted scene template + validated data
    Manim-->>Worker: Video and render metadata
    Worker->>QA: Video + storyboard + metadata
    QA-->>Worker: Pass or diagnostics
    alt QA passed
        Worker->>Store: Persist video, storyboard, QA report
        Store-->>UI: Artifact URL + timeline metadata
        UI->>UI: Play / pause / step / replay
    else QA failed
        Worker->>Queue: Bounded retry or failed status
        Note over UI: Text lesson remains available
    end
```

### Storyboard schema (conceptual)

Each storyboard should contain:
- `storyboard_version`, `problem_id`, `intent`, `language`, `learner_levels`
- `scenes[]`: scene ID, title, purpose, duration, narration/caption text
- `visual_objects[]`: object ID, type, initial state, labels and style token
- `steps[]`: step index, source trace state, visual changes, highlights, pointer/index changes, caption and duration
- `transitions[]`: from-state, to-state, transition type and duration
- `render_profile`: resolution, frame rate, theme and output format

Use stable object IDs and explicit before/after states. A storyboard step must map to a real trace state. Scene templates render arrays, maps, pointers, trees, graphs, stacks, queues, recursion frames and other structures using typed visual primitives.

### Render quality gates

- Storyboard schema and references are valid.
- State transitions are consistent with the algorithm trace.
- Video file exists, decodes, and has non-zero duration and frames.
- Resolution and frame rate match the render profile.
- Captions fit safe areas and remain readable.
- No missing visual objects, blank scenes or unexpected clipping.
- Render time, memory and output size stay within configured limits.
- Artifact is linked to the exact lesson/trace version used to create it.

## 7. API and data contracts

### Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/problems/{number}` | Canonical problem lookup |
| POST | `/api/learning-sessions` | Generate selected learning path |
| GET | `/api/learning-sessions/{session_id}` | Session and generation status |
| GET | `/api/animations/{animation_id}` | Animation status and artifact metadata |

Example request:

```json
{
  "problem_number": 1,
  "intent": "solve",
  "language": "cpp",
  "dsa_proficiency": "beginner",
  "programming_proficiency": "beginner",
  "animation": true
}
```

### Core schemas

- `ProblemDetails`: number, slug, title, difficulty, statement, examples, constraints, tags, canonical URL, source metadata.
- `LearnerConfig`: language enum and two independent proficiency enums.
- `LearningSessionRequest`: problem number, intent, learner config, animation preference.
- `SolutionLearningPlan`: observations, approaches, algorithm steps, correctness, complexity, implementation, syntax annotations and trace.
- `PrerequisiteLearningPath`: concept nodes, dependency edges, learning order, examples, checks and target-problem connection.
- `AlgorithmTrace`: ordered states and operations independent of programming language.
- `AnimationStoryboard`: typed scenes, visual objects, steps, transitions, captions and render profile.
- `AnimationArtifact`: ID, status, artifact URI, duration, dimensions, frame rate, storyboard/trace versions and QA report.

## 8. Component responsibilities and guardrails

| Component | Owns | Must not |
|---|---|---|
| Problem source adapter | Canonical question data | Invent missing source facts |
| Learner config | Language and separate proficiency axes | Collapse DSA and coding skill into one level |
| Solution generator | Teaching, approach, code and trace | Ignore selected language or levels |
| Prerequisite generator | Concept dependency curriculum | Reveal full solution by default |
| Syntax explainer | Explain constructs used in selected-language examples | Produce a generic language textbook |
| Trace builder | Deterministic algorithm states | Depend on animation rendering |
| Storyboard planner | Translate trace into visual lesson beats | Execute arbitrary generated code |
| Renderer adapter | Render typed storyboard with trusted templates | Accept arbitrary shell commands |
| QA worker | Validate output and report diagnostics | Mark failed/empty video as successful |
| Lesson UI | Display lesson and play artifact | Block text lesson if video fails |

## 9. Failure handling

- Problem lookup fails: no teaching or animation generation is started.
- Invalid learner configuration: return field-level validation errors.
- Teaching generation fails: retain problem and learner settings for retry.
- Storyboard invalid: bounded schema repair; do not queue invalid jobs.
- Renderer crashes or times out: mark animation failed, preserve lesson, expose retry.
- QA fails: bounded re-render; after retry budget, degrade to text/code.
- Artifact storage fails: retain render diagnostics and do not return a broken playback URL.

## 10. Scope and delivery sequence

1. Problem lookup and canonical problem schema.
2. Learner settings UI/API and independent proficiency handling.
3. Solve and prerequisite workflows.
4. Language-specific code generation and beginner syntax annotation.
5. Canonical trace schema shared by written lesson and animation.
6. Storyboard planner, schema/semantic validation and trusted scene templates.
7. Isolated Manim worker, render queue, QA and player.
8. End-to-end tests for all four languages, both intents, proficiency combinations and animation fallback.

Keep TTS, voice narration, accounts, analytics, other coding platforms and multi-agent expansion deferred until this vertical slice is reliable.
