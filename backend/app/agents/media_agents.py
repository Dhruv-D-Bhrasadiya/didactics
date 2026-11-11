import json
import logging
import shutil
import subprocess
from pathlib import Path
from backend.app.agents.prompt_loader import load_prompt
from backend.app.schemas.workflow import ScenePlan, MediaResult, SolutionPortfolio, ComplexityReport

log = logging.getLogger("didactics.media")

class Agent4ManimAnimator:
    name = "agent_4_manim_animator"
    def run(self, plan: ScenePlan, run_dir: Path, portfolio: SolutionPortfolio | None = None, complexity: ComplexityReport | None = None, repair_notes: list[str] | None = None) -> MediaResult:
        manim = shutil.which("manim")
        if not manim:
            raise RuntimeError("Manim executable not found. Install Manim, ffmpeg and a LaTeX distribution; see docs/RUNNING.md.")
        source_dir, media_dir = run_dir / "manim", run_dir / "media"
        source_dir.mkdir(parents=True, exist_ok=True)
        media_dir.mkdir(parents=True, exist_ok=True)
        variants = {v.variant_id: v for v in portfolio.approaches} if portfolio else {}
        rows = []
        for scene in plan.scenes:
            lines = list(scene.on_screen_text[:5])
            if scene.variant_id and scene.variant_id in variants:
                code_lines = variants[scene.variant_id].code.splitlines()[:8]
                lines += ["CODE: " + line[:82] for line in code_lines]
            if repair_notes:
                lines += ["QA FIX: " + note[:90] for note in repair_notes[:2]]
            rows.append({"title": scene.title, "objective": scene.objective, "text": lines[:8], "visual": scene.visual_direction, "duration": scene.duration_seconds})
        source_file = source_dir / "lesson_scene.py"
        source_file.write_text(self._template(rows), encoding="utf-8")
        (source_dir / "render_brief.txt").write_text(load_prompt("agent_4_manim"), encoding="utf-8")
        command = [manim, "-ql", "--disable_caching", "--media_dir", str(media_dir), str(source_file), "DidacticsLesson"]
        log.info("Agent 4 rendering %d scenes", len(rows))
        result = subprocess.run(command, capture_output=True, text=True, timeout=1200, cwd=str(run_dir))
        (run_dir / "logs" / "manim.stdout.log").write_text(result.stdout or "", encoding="utf-8")
        (run_dir / "logs" / "manim.stderr.log").write_text(result.stderr or "", encoding="utf-8")
        if result.returncode:
            raise RuntimeError("Manim render failed. See logs/manim.stderr.log")
        videos = sorted(media_dir.rglob("DidacticsLesson.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not videos:
            raise RuntimeError("Manim completed without producing the expected MP4.")
        target = run_dir / "lesson_video.mp4"
        shutil.copy2(videos[0], target)
        return MediaResult(video_path=str(target), rendered=True)

    @staticmethod
    def _template(rows: list[dict]) -> str:
        payload = json.dumps(rows, ensure_ascii=False)
        return '''from manim import *
import json
SCENES = json.loads(''' + repr(payload) + ''')
class DidacticsLesson(Scene):
    def construct(self):
        bg = Rectangle(width=14.2, height=8.0, fill_color="#0B0D0C", fill_opacity=1, stroke_width=0)
        self.add(bg)
        for index, item in enumerate(SCENES):
            title = Text(item["title"][:58], font_size=32, color="#C6F432", weight=BOLD).to_edge(UP, buff=0.55)
            objective = Text(item["objective"][:100], font_size=17, color=WHITE).next_to(title, DOWN, buff=0.28)
            lines = VGroup(*[Text(str(line)[:94], font_size=17 if str(line).startswith("CODE:") else 21, color="#DDE2D9") for line in item["text"][:8]])
            lines.arrange(DOWN, aligned_edge=LEFT, buff=0.2).move_to(ORIGIN).shift(DOWN*0.15)
            footer = Text(f"DIDACTICS | SCENE {index+1:02d}/{len(SCENES):02d}", font_size=12, color="#9AA39A").to_edge(DOWN, buff=0.25)
            group = VGroup(title, objective, lines, footer)
            self.play(FadeIn(title, shift=DOWN*0.12), run_time=0.4)
            self.play(FadeIn(objective), run_time=0.25)
            self.play(LaggedStart(*[FadeIn(line, shift=RIGHT*0.1) for line in lines], lag_ratio=0.08), run_time=0.8)
            self.add(footer)
            self.wait(max(1, item["duration"]-2))
            self.play(FadeOut(group), run_time=0.3)
'''

class Agent5AudioProducer:
    name = "agent_5_audio_producer"
    def run(self, plan: ScenePlan, run_dir: Path, repair_notes: list[str] | None = None) -> dict:
        try:
            import pyttsx3
        except ImportError as exc:
            raise RuntimeError("pyttsx3 missing; install backend requirements for offline TTS.") from exc
        audio_dir = run_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        (audio_dir / "production_brief.txt").write_text(load_prompt("agent_5_audio"), encoding="utf-8")
        if repair_notes:
            log.warning("Regenerating scene audio after QA feedback: %s", repair_notes[:5])
        engine = pyttsx3.init()
        engine.setProperty("rate", 165)
        segments = []
        for scene in plan.scenes:
            path = audio_dir / (scene.scene_id.replace("/", "_") + ".wav")
            engine.save_to_file(scene.narration, str(path))
            engine.runAndWait()
            if not path.exists() or path.stat().st_size < 1000:
                raise RuntimeError("TTS produced no valid audio for scene " + scene.scene_id)
            segments.append(path)
        engine.stop()
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("ffmpeg is required to concatenate scene narration.")
        concat_file = audio_dir / "concat.txt"
        concat_file.write_text("\n".join("file '" + p.as_posix().replace("'", "'\\''") + "'" for p in segments), encoding="utf-8")
        output = run_dir / "lesson_audio.wav"
        proc = subprocess.run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-ac", "1", "-ar", "24000", str(output)], capture_output=True, text=True, timeout=300)
        (run_dir / "logs" / "audio-render.log").write_text((proc.stdout or "") + "\n" + (proc.stderr or ""), encoding="utf-8")
        if proc.returncode:
            raise RuntimeError("Audio concatenation failed; see logs/audio-render.log")
        return {"audio_path": str(output), "segments": [str(p) for p in segments], "audio_generated": True}
