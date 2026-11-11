import json
import logging
import shutil
import subprocess
from pathlib import Path
from backend.app.schemas.workflow import QAReport, ScenePlan
from backend.app.agents.provider_runtime import invoke_structured
from backend.app.config import get_settings
from backend.app.agents.utils import secret_value

log = logging.getLogger("didactics.qa")

class Agent6MultimodalQA:
    name = "agent_6_multimodal_qa"

    def _inspect_frames(self, video_path: str | None) -> dict:
        if not video_path:
            return {"available": False}
        try:
            import cv2
            capture = cv2.VideoCapture(video_path)
            if not capture.isOpened():
                return {"available": False, "error": "Video decoder could not open the file."}
            frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = capture.get(cv2.CAP_PROP_FPS) or 0
            width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            samples = []
            for fraction in (0.1, 0.35, 0.6, 0.85):
                capture.set(cv2.CAP_PROP_POS_FRAMES, min(max(0, int(frame_count * fraction)), max(0, frame_count - 1)))
                ok, frame = capture.read()
                if ok:
                    samples.append({"position": fraction, "mean_luminance": round(float(frame.mean()), 2), "std_luminance": round(float(frame.std()), 2)})
            capture.release()
            return {"available": True, "frame_count": frame_count, "fps": fps, "width": width, "height": height, "sampled_frames": samples, "blank_frame_warning": any(x["std_luminance"] < 2 and x["mean_luminance"] < 5 for x in samples)}
        except Exception as exc:
            log.exception("Video frame inspection failed")
            return {"available": False, "error": str(exc)}

    def _transcribe_audio(self, audio_path: str | None) -> dict:
        if not audio_path or not Path(audio_path).is_file():
            return {"available": False, "reason": "Audio file missing"}
        settings = get_settings()
        key = secret_value(settings.groq_api_key)
        if not key:
            return {"available": False, "reason": "GROQ_API_KEY is not configured; narration transcript comparison skipped"}
        try:
            from groq import Groq
            with open(audio_path, "rb") as audio_file:
                transcript = Groq(api_key=key).audio.transcriptions.create(file=audio_file, model="whisper-large-v3-turbo", response_format="text")
            return {"available": True, "transcript": str(transcript)}
        except Exception as exc:
            log.exception("Audio transcription QA failed")
            return {"available": False, "error": str(exc)}

    def run(self, plan: ScenePlan, video_path: str | None, audio_path: str | None, run_dir: Path):
        ffprobe = shutil.which("ffprobe")
        checks = {"video_exists": bool(video_path and Path(video_path).is_file()), "audio_exists": bool(audio_path and Path(audio_path).is_file()), "frames": self._inspect_frames(video_path), "audio_transcription": self._transcribe_audio(audio_path), "video_probe": None, "audio_probe": None}
        if ffprobe and checks["video_exists"]:
            proc = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,r_frame_rate", "-of", "json", video_path], capture_output=True, text=True, timeout=30)
            if proc.returncode == 0:
                checks["video_probe"] = json.loads(proc.stdout)
            else:
                checks["video_probe_error"] = proc.stderr[-1000:]
        if ffprobe and checks["audio_exists"]:
            proc = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration:stream=codec_type,sample_rate,channels", "-of", "json", audio_path], capture_output=True, text=True, timeout=30)
            if proc.returncode == 0:
                checks["audio_probe"] = json.loads(proc.stdout)
            else:
                checks["audio_probe_error"] = proc.stderr[-1000:]
        payload = {"scene_plan": plan.model_dump(), "media_checks": checks}
        report, trace = invoke_structured(self.name,
            "You are a strict audiovisual lesson release reviewer. Compare the expected scene plan with actual frame inspection, audio transcription when available, and media probe evidence. Check narration coverage and missing/duplicated phrases, visual blank frames and dimensions, scene coverage, media decoding, durations and synchronization risks. If a transcript is unavailable, explicitly mark speech-content verification as not performed. Do not claim human-level perceptual review. If either media file is missing, fail. Return a result for every scene and actionable repair tickets.",
            "Review the lesson and captured evidence:\n" + json.dumps(payload, ensure_ascii=False), QAReport)
        expected = {scene.scene_id for scene in plan.scenes}
        observed = {scene.scene_id for scene in report.scene_results}
        if expected != observed:
            raise ValueError(f"QA scene coverage mismatch. Missing={sorted(expected-observed)}")
        if not checks["video_exists"] or not checks["audio_exists"] or checks["frames"].get("blank_frame_warning"):
            report.passed = False
        report.media_checks = checks
        return report, trace
