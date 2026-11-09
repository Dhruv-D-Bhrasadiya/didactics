from functools import lru_cache
from pathlib import Path

# Locate the absolute path of the prompts directory
PROMPTS_DIR = Path(__file__).parent

@lru_cache()
def load_prompt(file_path: str) -> str:
    """Read a prompt file relative to the prompts directory and cache it.

    Args:
        file_path: Prompt filename within the prompts directory.

    Returns:
        str: Prompt text with leading and trailing whitespace removed.

    Raises:
        FileNotFoundError: If the requested prompt file does not exist.

    Example:
        system_prompt = load_prompt("request_understanding_agent.yaml")
    """
    full_path = PROMPTS_DIR / file_path
    
    if not full_path.exists():
        raise FileNotFoundError(f"Prompt file not found at: {full_path}")
        
    return full_path.read_text(encoding="utf-8").strip()
