from collections.abc import Callable


class BaseAgent:
    """Common LLM lifecycle behavior shared by agents."""

    def __init__(self, model_name: str, api_keys: list[str], llm_builder: Callable):
        if not api_keys:
            raise ValueError("At least one API key is required")

        self.model_name = model_name
        self.api_keys = [key for key in api_keys if key]
        if not self.api_keys:
            raise ValueError("At least one non-empty API key is required")

        self.llm_builder = llm_builder
        self.current_key_index = 0
        self.llm = self._build_llm()

    def _build_llm(self):
        api_key = self.api_keys[self.current_key_index]
        return self.llm_builder(api_key, self.model_name)

    def rotate_key(self) -> None:
        """Rotate to the next configured API key and rebuild the LLM."""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self.llm = self._build_llm()