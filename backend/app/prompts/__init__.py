from functools import lru_cache
from pathlib import Path

# Locate the absolute path of the prompts directory
PROMPTS_DIR = Path(__file__).parent

@lru_cache()
def load_prompt(file_path: str) -> str:
    """Reads a prompt text file once and caches it in memory."""
    full_path = PROMPTS_DIR / file_path
    
    if not full_path.exists():
        raise FileNotFoundError(f"Prompt file not found at: {full_path}")
        
    return full_path.read_text(encoding="utf-8").strip()
