import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from backend.app.storage.out_manager import write_json
log=logging.getLogger("didactics.checkpoints")
class CheckpointManager:
    def __init__(self, run_dir: Path):
        self.run_dir=run_dir; self.checkpoint_dir=run_dir/"checkpoints"; self.checkpoint_dir.mkdir(parents=True,exist_ok=True)
    def save(self, stage_name: str, payload: Any) -> Path:
        safe="".join(c if c.isalnum() or c in "-_" else "_" for c in stage_name)
        path=self.checkpoint_dir/f"{safe}.json"
        write_json(path,{"stage":stage_name,"saved_at":datetime.now(timezone.utc).isoformat(),"data":payload})
        log.info("Checkpoint saved: %s",path); return path
    def save_failure(self,error:Exception,traceback_text:str,completed_stages:list[str])->Path:
        return self.save("failure",{"error_type":type(error).__name__,"error":str(error),"traceback":traceback_text,"completed_stages":completed_stages})
