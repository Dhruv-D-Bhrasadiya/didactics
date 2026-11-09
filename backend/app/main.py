"""FastAPI endpoints for canonical problem lookup and learner configuration."""
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.app.schemas.learner import LearnerConfigRequest, build_learning_profile
from backend.app.services.leetcode_source import (
    PremiumProblem, ProblemNotFound, ProblemRateLimited,
    ProblemSourceUnavailable, fetch_problem,
)

app = FastAPI(
    title="Didactics API",
    description="Canonical LeetCode problem lookup and learner configuration validation.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "didactics-api"}


@app.get("/api/problems/{problem_number}")
async def get_problem(problem_number: str):
    if not re.fullmatch(r"[1-9][0-9]{0,5}", problem_number):
        raise HTTPException(status_code=400, detail={
            "code": "INVALID_PROBLEM_NUMBER",
            "message": "Enter a positive whole-number LeetCode problem ID.",
        })
    try:
        return await fetch_problem(int(problem_number))
    except ProblemNotFound:
        raise HTTPException(status_code=404, detail={
            "code": "PROBLEM_NOT_FOUND",
            "message": f"No LeetCode problem was found for number {problem_number}.",
        })
    except PremiumProblem:
        raise HTTPException(status_code=403, detail={
            "code": "PREMIUM_PROBLEM",
            "message": "This problem is premium-only and its statement is not publicly available.",
        })
    except ProblemRateLimited:
        raise HTTPException(status_code=429, detail={
            "code": "SOURCE_RATE_LIMITED",
            "message": "LeetCode is rate-limiting requests. Please wait and try again.",
        })
    except ProblemSourceUnavailable as exc:
        raise HTTPException(status_code=502, detail={
            "code": "SOURCE_UNAVAILABLE",
            "message": str(exc),
        })


@app.post("/api/learner-config/validate")
async def validate_learner_config(config: LearnerConfigRequest):
    return {"valid": True, "profile": build_learning_profile(config)}
