from app.config import get_settings 
from groq import Groq 
from google import genai  # Import the official GenAI SDK

settings = get_settings() 

# Initialize the clients
groq_client = Groq(api_key=settings.groq_api_key.get_secret_value())
gemini_client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())

class CheckModel:
    """Provide command-line checks for models available to configured providers.

    The static methods list the models returned by the Groq and Gemini APIs.

    Example:
        CheckModel.gemini_model_check()
    """

    @staticmethod
    def qroq_model_check():
        """Print the models available through the configured Groq client.

        Args:
            None.

        Returns:
            None: Writes model identifiers or an error message to stdout.

        Example:
            CheckModel.qroq_model_check()
        """
        try:
            models_list = groq_client.models.list()
            print("--- Available Groq Models ---")
            for model in models_list.data:
                print(f"- {model.id}")
        except Exception as e:
            print(f"An error occurred with Groq: {e}")

    @staticmethod
    def gemini_model_check():
        """Print the models and supported actions available through Gemini.

        Args:
            None.

        Returns:
            None: Writes model details or an error message to stdout.

        Example:
            CheckModel.gemini_model_check()
        """
        try:
            models_list = gemini_client.models.list()
            print("\n--- Available Gemini Models ---")
            for model in models_list:
                print(f"- {model.name} (Supported actions: {model.supported_actions})")
        except Exception as e:
            print(f"An error occurred with Gemini: {e}")


class CheckUsage:
    """Print provider usage limits and token-related information.

    The methods inspect Groq rate-limit headers and Gemini context/token
    metadata. Financial credit balances must be viewed in provider consoles.

    Example:
        CheckUsage.groq_rate_limits("openai/gpt-oss-20b")
    """

    @staticmethod
    def groq_rate_limits(model_name: str = "openai/gpt-oss-20b"):
        """Print Groq rate-limit metadata returned by a minimal API request.

        Args:
            model_name: Groq model used to make the metadata request.

        Returns:
            None: Writes returned rate-limit values or an error to stdout.

        Example:
            CheckUsage.groq_rate_limits("openai/gpt-oss-20b")
        """
        try:
            print("--- Groq Rate Limits & Usage Status ---")
            # We make a dummy low-token call to extract the headers
            chat_completion = groq_client.chat.completions.with_raw_response.create(
                messages=[{"role": "user", "content": "ping"}],
                model=model_name,
            )
            headers = chat_completion.headers
            
            # Extract rate limit metadata from headers
            print(f"- Remaining Requests today (RPD): {headers.get('x-ratelimit-remaining-requests')}")
            print(f"- Remaining Tokens this minute (TPM): {headers.get('x-ratelimit-remaining-tokens')}")
            print(f"- Total Limit Requests per day: {headers.get('x-ratelimit-limit-requests')}")
            print(f"- Total Limit Tokens per minute: {headers.get('x-ratelimit-limit-tokens')}")
            print(f"- Limit Reset Time (Tokens): {headers.get('x-ratelimit-reset-tokens')}")
        except Exception as e:
            print(f"An error occurred fetching Groq usage: {e}")

    @staticmethod
    def gemini_context_limits(model_name: str = "gemini-3.8-flash"):
        """Print Gemini's configured input and output token limits.

        Args:
            model_name: Gemini model whose limits should be retrieved.

        Returns:
            None: Writes context limits or an error message to stdout.

        Example:
            CheckUsage.gemini_context_limits("gemini-3.8-flash")
        """
        try:
            print(f"\n--- Gemini Limits for {model_name} ---")
            model_info = gemini_client.models.get(model=model_name)
            print(f"- Input Token Limit: {model_info.input_token_limit}")
            print(f"- Output Token Limit: {model_info.output_token_limit}")
        except Exception as e:
            print(f"An error occurred fetching Gemini limits: {e}")

    @staticmethod
    def gemini_count_tokens(text_prompt: str, model_name: str = "gemini-3.8-flash"):
        """Print Gemini's estimated token count for a prompt.

        Args:
            text_prompt: Text to count before sending it to the model.
            model_name: Gemini model used for token counting.

        Returns:
            None: Writes the prompt and token count or an error to stdout.

        Example:
            CheckUsage.gemini_count_tokens("Explain recursion")
        """
        try:
            print(f"\n--- Gemini Pre-flight Token Count ---")
            response = gemini_client.models.count_tokens(
                model=model_name,
                contents=text_prompt
            )
            print(f"- Prompt: \"{text_prompt}\"")
            print(f"- Total Tokens Required: {response.total_tokens}")
        except Exception as e:
            print(f"An error occurred counting Gemini tokens: {e}")


# Example usage:
if __name__ == "__main__":
    # 1. Fetch available platforms models
    CheckModel.qroq_model_check()
    CheckModel.gemini_model_check()

    # 2. Check rate limits and active day capacity for Groq (using active model)
    CheckUsage.groq_rate_limits("openai/gpt-oss-20b")
    
    # 3. Check structural parameters for Gemini (using gemini-3.8-flash)
    CheckUsage.gemini_context_limits("gemini-3.8-flash")
    
    # 4. Calculate text usage weight before running operations
    CheckUsage.gemini_count_tokens("How many credits does this sentence take?", "gemini-3.8-flash")