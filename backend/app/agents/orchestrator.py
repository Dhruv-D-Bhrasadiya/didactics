import json
import logging
import shutil
import subprocess
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend.app.agents.solution_agent import Agent1SolutionStrategist
from backend.app.agents.complexity_agent import Agent2ComplexityAnalyst
from backend.app.agents.lesson_director_agent import Agent3LessonDirector
from backend.app.agents.media_agents import Agent4ManimAnimator, Agent5AudioProducer
from backend.app.agents.qa_agent import Agent6MultimodalQA
from backend.app.schemas.workflow import GenerateSessionRequest

log = logging.getLogger("didactics.workflow")
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "out"

def _save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=lambda x: x.model_dump(mode="json") if hasattr(x, "model_dump") else str(x)) + "\n", encoding="utf-8")
    temporary.replace(path)

def _checkpoint(run_dir: Path, stage: str, data):
    path = run_dir / "checkpoints" / (stage + ".json")
    _save_json(path, {"stage": stage, "saved_at": datetime.now(timezone.utc).isoformat(), "data": data})
    log.info("Checkpoint saved: %s", path)
    return path

def _mux(video: str | None, audio: str | None, run_dir: Path) -> str | None:
    ffmpeg = shutil.which("ffmpeg")
    if not video or not audio or not ffmpeg:
        return video
    output = run_dir / "lesson_with_audio.mp4"
    command = [ffmpeg, "-y", "-i", video, "-i", audio, "-filter_complex", "[0:v]tpad=stop_mode=clone:stop_duration=600[v]", "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", "-shortest", str(output)]
    proc = subprocess.run(command, capture_output=True, text=True, timeout=600)
    (run_dir / "logs" / "mux.log").write_text((proc.stdout or "") + "\n" + (proc.stderr or ""), encoding="utf-8")
    if proc.returncode:
        raise RuntimeError("Video/audio mux failed; see logs/mux.log")
    return str(output)

def run_learning_workflow(problem: dict, request: GenerateSessionRequest, learner_profile: dict) -> dict:
    run_id = uuid4().hex
    run_dir = OUT / "runs" / run_id
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    (run_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
    result = {"run_id": run_id, "status": "running", "run_dir": str(run_dir), "completed_stages": [], "warnings": []}
    _save_json(run_dir / "run.json", {"run_id": run_id, "created_at": datetime.now(timezone.utc).isoformat(), "problem": problem, "request": request.model_dump(), "learner_profile": learner_profile})
    _checkpoint(run_dir, "00_input_validated", {"problem": problem, "request": request, "learner_profile": learner_profile})
    log.info("Starting workflow run=%s problem=%s", run_id, request.problem_number)
    learner = {**learner_profile, "intent": request.intent}
    try:
        portfolio, trace1 = Agent1SolutionStrategist().run(problem, learner)
        _checkpoint(run_dir, "01_solution_portfolio", {"portfolio": portfolio, "trace": trace1})
        result["completed_stages"].append("agent_1_solution_strategist")

        complexity, trace2 = Agent2ComplexityAnalyst().run(portfolio, problem)
        _checkpoint(run_dir, "02_complexity_report", {"report": complexity, "trace": trace2})
        result["completed_stages"].append("agent_2_complexity_analyst")

        plan, trace3 = Agent3LessonDirector().run(problem, portfolio, complexity, learner)
        _checkpoint(run_dir, "03_scene_plan", {"plan": plan, "trace": trace3})
        result["completed_stages"].append("agent_3_lesson_director")

        media_errors = []
        def render_visuals():
            return Agent4ManimAnimator().run(plan, run_dir, portfolio, complexity)
        def render_audio():
            return Agent5AudioProducer().run(plan, run_dir)
        # Visual and audio production are independent and run concurrently.
        with ThreadPoolExecutor(max_workers=2) as pool:
            visual_future, audio_future = pool.submit(render_visuals), pool.submit(render_audio)
            try:
                visual = visual_future.result()
                media = visual.model_dump(mode="json")
                _checkpoint(run_dir, "04_animation_bundle", media)
                result["completed_stages"].append("agent_4_manim_animator")
            except Exception as exc:
                media_errors.append("Agent 4: " + str(exc))
                log.exception("Agent 4 failed run=%s", run_id)
                _save_json(run_dir / "checkpoints" / "04_animation_error.json", {"error": str(exc), "traceback": traceback.format_exc()})
                media = {"video_path": None, "rendered": False}
            try:
                audio = audio_future.result()
                media.update(audio)
                _checkpoint(run_dir, "05_audio_bundle", audio)
                result["completed_stages"].append("agent_5_audio_producer")
            except Exception as exc:
                media_errors.append("Agent 5: " + str(exc))
                log.exception("Agent 5 failed run=%s", run_id)
                _save_json(run_dir / "checkpoints" / "05_audio_error.json", {"error": str(exc), "traceback": traceback.format_exc()})
        final_video = _mux(media.get("video_path"), media.get("audio_path"), run_dir)
        if final_video:
            media["video_path"] = final_video
        _checkpoint(run_dir, "05_media_composition", media)

        qa, trace6 = Agent6MultimodalQA().run(plan, media.get("video_path"), media.get("audio_path"), run_dir)
        _checkpoint(run_dir, "06_qa_report", {"report": qa, "trace": trace6})
        result["completed_stages"].append("agent_6_multimodal_qa")
        result["warnings"].extend(media_errors)
        result.update({
            "status": "completed" if qa.passed else "needs_review",
            "lesson_title": plan.lesson_title,
            "solution_portfolio": portfolio.model_dump(mode="json"),
            "complexity_report": complexity.model_dump(mode="json"),
            "scene_plan": plan.model_dump(mode="json"),
            "media": media,
            "qa_report": qa.model_dump(mode="json"),
            "artifacts": {"run_dir": str(run_dir), "checkpoints_dir": str(run_dir / "checkpoints"), "logs_dir": str(run_dir / "logs")},
        })
        _save_json(run_dir / "result.json", result)
        _save_json(run_dir / "manifest.json", {"run_id": run_id, "status": result["status"], "completed_stages": result["completed_stages"], "files": [str(p.relative_to(run_dir)) for p in run_dir.rglob("*") if p.is_file()]})
        log.info("Workflow finished run=%s status=%s", run_id, result["status"])
        return result
    except Exception as exc:
        log.exception("Workflow failed run=%s", run_id)
        result.update({"status": "failed", "error": str(exc), "failed_at": datetime.now(timezone.utc).isoformat(), "artifacts": {"run_dir": str(run_dir), "checkpoints_dir": str(run_dir / "checkpoints"), "logs_dir": str(run_dir / "logs")}})
        _save_json(run_dir / "failure.json", {"error": str(exc), "traceback": traceback.format_exc(), "completed_stages": result["completed_stages"]})
        _save_json(run_dir / "result.json", result)
        return result
