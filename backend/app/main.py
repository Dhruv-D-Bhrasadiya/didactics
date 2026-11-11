"""FastAPI endpoints for problem lookup and six-agent lesson generation."""
import logging
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.agents.orchestrator import run_learning_workflow
from backend.app.logging_config import configure_logging
from backend.app.schemas.learner import LearnerConfigRequest, build_learning_profile
from backend.app.schemas.workflow import GenerateSessionRequest
from backend.app.services.leetcode_source import (
    PremiumProblem, ProblemNotFound, ProblemRateLimited,
    ProblemSourceUnavailable, fetch_problem,
)

configure_logging()
logger = logging.getLogger("didactics.api")

app = FastAPI(title="Didactics API", description="Six-agent LeetCode teaching and media generation workflow.", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "didactics-api", "workflow": "six-agent"}

@app.get("/api/problems/{problem_number}")
async def get_problem(problem_number: str):
    if not re.fullmatch(r"[1-9][0-9]{0,5}", problem_number):
        raise HTTPException(status_code=400, detail={"code": "INVALID_PROBLEM_NUMBER", "message": "Enter a positive whole-number LeetCode problem ID."})
    try:
        return await fetch_problem(int(problem_number))
    except ProblemNotFound:
        raise HTTPException(status_code=404, detail={"code": "PROBLEM_NOT_FOUND", "message": f"No LeetCode problem was found for number {problem_number}."})
    except PremiumProblem:
        raise HTTPException(status_code=403, detail={"code": "PREMIUM_PROBLEM", "message": "This problem is premium-only and its statement is not publicly available."})
    except ProblemRateLimited:
        raise HTTPException(status_code=429, detail={"code": "SOURCE_RATE_LIMITED", "message": "LeetCode is rate-limiting requests. Please wait and try again."})
    except ProblemSourceUnavailable as exc:
        logger.exception("Problem source lookup failed for %s", problem_number)
        raise HTTPException(status_code=502, detail={"code": "SOURCE_UNAVAILABLE", "message": str(exc)})

@app.post("/api/learner-config/validate")
async def validate_learner_config(config: LearnerConfigRequest):
    return {"valid": True, "profile": build_learning_profile(config)}

@app.post("/api/sessions/generate")
async def generate_learning_session(request: GenerateSessionRequest):
    """Fetch the source problem and execute the durable six-agent workflow."""
    try:
        problem = await fetch_problem(request.problem_number)
    except ProblemNotFound:
        raise HTTPException(status_code=404, detail={"code": "PROBLEM_NOT_FOUND", "message": "LeetCode problem was not found."})
    except PremiumProblem:
        raise HTTPException(status_code=403, detail={"code": "PREMIUM_PROBLEM", "message": "Premium problem statements are unavailable."})
    except ProblemRateLimited:
        raise HTTPException(status_code=429, detail={"code": "SOURCE_RATE_LIMITED", "message": "Problem source rate limit reached."})
    except ProblemSourceUnavailable as exc:
        logger.exception("Problem source failed before agent workflow")
        raise HTTPException(status_code=502, detail={"code": "SOURCE_UNAVAILABLE", "message": str(exc)})

    config = LearnerConfigRequest(language=request.language, dsa_proficiency=request.dsa_proficiency, programming_proficiency=request.programming_proficiency)
    profile = build_learning_profile(config)
    result = await run_in_threadpool(run_learning_workflow, problem, request, profile)
    if result.get("status") == "failed":
        logger.error("Workflow failed run_id=%s error=%s", result.get("run_id"), result.get("error"))
    return result

OUT_DIR = Path(__file__).resolve().parents[2] / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/artifacts", StaticFiles(directory=str(OUT_DIR), check_dir=True), name="artifacts")
