# Didactics frontend

A responsive React + Vite interface for the focused LeetCode tutor journey.

## Run locally

From this directory:

```bash
npm install
npm run dev
```

Create a production build:

```bash
npm run build
```

## Current scope

The UI covers the first seven functional requirements:

1. Language selection — Java, Python, C and C++.
2. Independent DSA and programming proficiency.
3. Beginner programming syntax-support messaging.
4. Positive LeetCode problem-number input and validation.
5. Problem details review/confirmation.
6. Explicit learning-intent choice.
7. Route selection for solution walkthrough or prerequisite learning.

Problem #1 (Two Sum) is included as a clearly labelled demo fixture. Other numbers show a connection notice because the canonical LeetCode lookup API is not yet implemented. The final session action currently previews the learner configuration; it does not call a generation backend.

## Next integration

Connect the problem form to `GET /api/problems/{number}`, then submit the confirmed problem and learner settings to `POST /api/learning-sessions`. Replace the demo fixture and local confirmation with the API response and session status.
