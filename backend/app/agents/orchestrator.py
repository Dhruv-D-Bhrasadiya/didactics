import json
import logging
import shutil
import subprocess
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from backend.app.agents.solution_agent import Agent1SolutionStrategist
from backend.app.agents.complexity_agent import Agent2ComplexityAnalyst
from backend.app.agents.lesson_director_agent import Agent3LessonDirector
from backend.app.agents.media_agents import Agent4ManimAnimator, Agent5AudioProducer
from backend.app.agents.qa_agent import Agent6MultimodalQA
from backend.app.schemas.workflow import GenerateSessionRequest
from backend.app.storage.out_manager import create_run_directory, write_json, write_run_manifest
from backend.app.storage.checkpoint_manager import CheckpointManager

log = logging.getLogger("didactics.workflow")
MAX_QA_REPAIR_CYCLES = 3

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

def _ticket_notes(report, target: str) -> list[str]:
    notes = []
    for ticket in report.repair_tickets:
        route = str(ticket.get("target_agent", ticket.get("agent", ""))).lower()
        kind = str(ticket.get("type", ticket.get("category", ""))).lower()
        if target in route or target in kind or (target == "visual" and "agent_4" in route) or (target == "audio" and "agent_5" in route) or "sync" in kind or "sync" in route:
            notes.append(str(ticket.get("issue", ticket.get("required_change", ticket))))
    return notes[:8]

def run_learning_workflow(problem: dict, request: GenerateSessionRequest, learner_profile: dict) -> dict:
    run_id, run_dir = create_run_directory()
    checkpoints = CheckpointManager(run_dir)
    result = {"run_id": run_id, "status": "running", "run_dir": str(run_dir), "completed_stages": [], "warnings": []}
    write_json(run_dir / "run.json", {"run_id": run_id, "created_at": datetime.now(timezone.utc).isoformat(), "problem": problem, "request": request.model_dump(), "learner_profile": learner_profile})
    checkpoints.save("00_input_validated", {"problem": problem, "request": request, "learner_profile": learner_profile})
    log.info("Starting workflow run=%s problem=%s", run_id, request.problem_number)
    learner = {**learner_profile, "intent": request.intent}
    try:
        portfolio, trace1 = Agent1SolutionStrategist().run(problem, learner)
        checkpoints.save("01_solution_portfolio", {"portfolio": portfolio, "trace": trace1})
        result["completed_stages"].append("agent_1_solution_strategist")

        complexity, trace2 = Agent2ComplexityAnalyst().run(portfolio, problem)
        checkpoints.save("02_complexity_report", {"report": complexity, "trace": trace2})
        result["completed_stages"].append("agent_2_complexity_analyst")

        plan, trace3 = Agent3LessonDirector().run(problem, portfolio, complexity, learner)
        checkpoints.save("03_scene_plan", {"plan": plan, "trace": trace3})
        result["completed_stages"].append("agent_3_lesson_director")

        media = {"video_path": None, "audio_path": None, "rendered": False, "audio_generated": False}
        qa = None
        repair_notes = []
        for attempt in range(1, MAX_QA_REPAIR_CYCLES + 1):
            log.info("Media production and QA attempt %d/%d run=%s", attempt, MAX_QA_REPAIR_CYCLES, run_id)
            errors = []
            with ThreadPoolExecutor(max_workers=2) as pool:
                visual_future = pool.submit(Agent4ManimAnimator().run, plan, run_dir, portfolio, complexity, _ticket_notes(qa, "visual") if qa else repair_notes)
                audio_future = pool.submit(Agent5AudioProducer().run, plan, run_dir, _ticket_notes(qa, "audio") if qa else repair_notes)
                try:
                    visual = visual_future.result()
                    media.update(visual.model_dump(mode="json"))
                    checkpoints.save(f"04_animation_bundle_attempt_{attempt}", media)
                    if "agent_4_manim_animator" not in result["completed_stages"]:
                        result["completed_stages"].append("agent_4_manim_animator")
                except Exception as exc:
                    errors.append("Agent 4: " + str(exc))
                    log.exception("Agent 4 failed attempt=%s run=%s", attempt, run_id)
                    checkpoints.save(f"04_animation_error_attempt_{attempt}", {"error": str(exc), "traceback": traceback.format_exc()})
                    media["video_path"] = None
                try:
                    audio = audio_future.result()
                    media.update(audio)
                    checkpoints.save(f"05_audio_bundle_attempt_{attempt}", audio)
                    if "agent_5_audio_producer" not in result["completed_stages"]:
                        result["completed_stages"].append("agent_5_audio_producer")
                except Exception as exc:
                    errors.append("Agent 5: " + str(exc))
                    log.exception("Agent 5 failed attempt=%s run=%s", attempt, run_id)
                    checkpoints.save(f"05_audio_error_attempt_{attempt}", {"error": str(exc), "traceback": traceback.format_exc()})
                    media["audio_path"] = None
            result["warnings"].extend(errors)
            final_video = _mux(media.get("video_path"), media.get("audio_path"), run_dir)
            if final_video:
                media["video_path"] = final_video
            checkpoints.save(f"05_media_composition_attempt_{attempt}", media)

            qa, trace6 = Agent6MultimodalQA().run(plan, media.get("video_path"), media.get("audio_path"), run_dir)
            checkpoints.save(f"06_qa_attempt_{attempt}", {"report": qa, "trace": trace6})
            if qa.passed:
                break
            repair_notes = [str(ticket.get("issue", ticket.get("required_change", ticket))) for ticket in qa.repair_tickets]
            if not repair_notes:
                repair_notes = [finding for scene in qa.scene_results for finding in scene.findings]
            if attempt < MAX_QA_REPAIR_CYCLES:
                log.warning("QA rejected media; routing %d repair notes for another attempt", len(repair_notes))
        checkpoints.save("06_qa_report", {"report": qa, "trace": trace6, "attempts": attempt, "max_repair_cycles": MAX_QA_REPAIR_CYCLES})
        result["completed_stages"].append("agent_6_multimodal_qa")
        result.update({
            "status": "completed" if qa.passed else "needs_review",
            "lesson_title": plan.lesson_title,
            "solution_portfolio": portfolio.model_dump(mode="json"),
            "complexity_report": complexity.model_dump(mode="json"),
            "scene_plan": plan.model_dump(mode="json"),
            "media": media,
            "qa_report": qa.model_dump(mode="json"),
            "qa_attempts": attempt,
            "artifacts": {"run_dir": str(run_dir), "checkpoints_dir": str(run_dir / "checkpoints"), "logs_dir": str(run_dir / "logs")},
        })
        write_json(run_dir / "result.json", result)
        write_run_manifest(run_dir, result)
        log.info("Workflow finished run=%s status=%s", run_id, result["status"])
        return result
    except Exception as exc:
        log.exception("Workflow failed run=%s", run_id)
        result.update({"status": "failed", "error": str(exc), "failed_at": datetime.now(timezone.utc).isoformat(), "artifacts": {"run_dir": str(run_dir), "checkpoints_dir": str(run_dir / "checkpoints"), "logs_dir": str(run_dir / "logs")}})
        checkpoints.save_failure(exc, traceback.format_exc(), result["completed_stages"])
        write_json(run_dir / "result.json", result)
        return result
