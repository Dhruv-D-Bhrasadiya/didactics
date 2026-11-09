from collections.abc import Callable

from pydantic import BaseModel

class BaseAgent:
    """Provide shared language-model configuration and API-key lifecycle.

    The class validates the configured keys, constructs the selected model
    through the supplied builder, and can rotate to the next key.

    Example:
        agent = BaseAgent("model-id", ["key"], lambda key, model: client)
    """

    def __init__(
        self,
        model_name: str,
        api_keys: list[str],
        llm_builder: Callable,
        provider: str = "",
        output_type: type[BaseModel] | None = None,
    ):
        """Validate configuration and build the initial language model.

        Args:
            model_name: Provider-specific model identifier.
            api_keys: Ordered API keys to use, with the first tried initially.
            llm_builder: Callable that receives an API key and model name.
            provider: Optional provider identifier recorded in execution traces.
            output_type: Optional Pydantic model expected from model output.

        Returns:
            None: Initializes the agent instance.

        Example:
            agent = BaseAgent("model-id", ["key"], lambda key, model: client)
        """
        if not api_keys:
            raise ValueError("At least one API key is required")

        self.model_name = model_name
        self.api_keys = [key for key in api_keys if key]
        if not self.api_keys:
            raise ValueError("At least one non-empty API key is required")

        self.llm_builder = llm_builder
        self.provider = provider
        self.output_type = output_type
        self.current_key_index = 0
        self.llm = self._build_llm()

    def _build_llm(self):
        """Build a model client using the currently selected API key.

        Args:
            None.

        Returns:
            Any: The model instance returned by ``llm_builder``.

        Example:
            llm = agent._build_llm()
        """
        api_key = self.api_keys[self.current_key_index]
        return self.llm_builder(api_key, self.model_name)

    def rotate_key(self) -> None:
        """Advance to the next key and rebuild the language model.

        Rotation wraps around when the final configured key is reached.

        Args:
            None.

        Returns:
            None: Updates ``current_key_index`` and ``llm`` in place.

        Example:
            agent.rotate_key()
        """
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self.llm = self._build_llm()