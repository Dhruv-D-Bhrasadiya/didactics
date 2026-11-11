"""Agent 6: audiovisual QA with explicit skipped checks."""
import json, logging, shutil, subprocess
from pathlib import Path
from backend.app.agents.prompt_loader import load_prompt
from backend.app.agents.provider_runtime import invoke_structured
from backend.app.config import get_settings
from backend.app.agents.utils import secret_value
from backend.app.schemas.workflow import QAReport, ScenePlan
log = logging.getLogger("didactics.qa")

class Agent6MultimodalQA:
    name = "agent_6_multimodal_qa"
    def _inspect_frames(self, path):
        if not path: return {"available": False}
        try:
            import cv2
            cap = cv2.VideoCapture(path)
            if not cap.isOpened(): return {"available": False, "error": "Video decoder could not open the file."}
            count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); samples = []
            for pos in (0.1, 0.35, 0.6, 0.85):
                cap.set(cv2.CAP_PROP_POS_FRAMES, min(max(0, int(count*pos)), max(0, count-1)))
                ok, frame = cap.read()
                if ok: samples.append({"position":pos,"mean_luminance":round(float(frame.mean()),2),"std_luminance":round(float(frame.std()),2)})
            result={"available":True,"frame_count":count,"fps":cap.get(cv2.CAP_PROP_FPS) or 0,"width":int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),"height":int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),"sampled_frames":samples}
            cap.release(); result["blank_frame_warning"]=any(x["std_luminance"]<2 and x["mean_luminance"]<5 for x in samples)
            return result
        except Exception as exc:
            log.exception("Video frame inspection failed"); return {"available":False,"error":str(exc)}
    def _transcribe_audio(self, path):
        if not path or not Path(path).is_file(): return {"available":False,"reason":"Audio file missing"}
        key=secret_value(get_settings().groq_api_key)
        if not key: return {"available":False,"reason":"GROQ_API_KEY is not configured; transcript verification skipped"}
        try:
            from groq import Groq
            with open(path,"rb") as stream: text=Groq(api_key=key).audio.transcriptions.create(file=stream,model="whisper-large-v3-turbo",response_format="text")
            return {"available":True,"transcript":str(text)}
        except Exception as exc:
            log.exception("Audio transcription failed"); return {"available":False,"error":str(exc)}
    def run(self, plan: ScenePlan, video_path: str|None, audio_path: str|None, run_dir: Path):
        checks={"video_exists":bool(video_path and Path(video_path).is_file()),"audio_exists":bool(audio_path and Path(audio_path).is_file()),"frames":self._inspect_frames(video_path),"audio_transcription":self._transcribe_audio(audio_path)}
        ffprobe=shutil.which("ffprobe")
        for key,path in (("video_probe",video_path),("audio_probe",audio_path)):
            if ffprobe and path and Path(path).is_file():
                proc=subprocess.run([ffprobe,"-v","error","-show_entries","format=duration:stream=codec_type,width,height,r_frame_rate,sample_rate,channels","-of","json",path],capture_output=True,text=True,timeout=30)
                checks[key]=json.loads(proc.stdout) if proc.returncode==0 else {"error":proc.stderr[-1000:]}
        payload={"scene_plan":plan.model_dump(mode="json"),"media_checks":checks}
        report,trace=invoke_structured(self.name,load_prompt("agent_6_qa"),"Review this lesson and captured media evidence:\n"+json.dumps(payload,ensure_ascii=False),QAReport)
        expected={scene.scene_id for scene in plan.scenes}; observed={scene.scene_id for scene in report.scene_results}
        if expected!=observed: raise ValueError(f"QA scene coverage mismatch. Missing={sorted(expected-observed)}")
        if not checks["video_exists"] or not checks["audio_exists"] or checks["frames"].get("blank_frame_warning"): report.passed=False
        report.media_checks=checks
        return report,trace
