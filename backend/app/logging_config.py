import logging
from pathlib import Path

def configure_logging():
    root = Path(__file__).resolve().parents[2]
    log_dir = root / "out" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    file_handler = logging.FileHandler(log_dir / "didactics.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=[console, file_handler], force=True)
