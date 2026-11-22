from backend.app.configs.config import get_settings 
from groq import Groq 
from google import genai  

settings = get_settings() 

groq_client = Groq(api_key=settings.groq_api_key.get_secret_value())
gemini_client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())

class CheckModel:

    @staticmethod
    def groq_model_check():
        try:
            models_list = groq_client.models.list()
            print("--- Available Groq Models ---")
            for model in models_list.data:
                print(f"- {model.id}")
        except Exception as e:
            print(f"An error occurred with Groq: {e}")

    @staticmethod
    def gemini_model_check():
        try:
            models_list = gemini_client.models.list()
            print("\n--- Available Gemini Models ---")
            for model in models_list:
                print(f"- {model.name} (Supported actions: {model.supported_actions})")
        except Exception as e:
            print(f"An error occurred with Gemini: {e}")


class CheckUsage:

    @staticmethod
    def groq_rate_limits(model_name: str = "openai/gpt-oss-20b"):
        
        try:
            print("--- Groq Rate Limits & Usage Status ---")
            chat_completion = groq_client.chat.completions.with_raw_response.create(
                messages=[{"role": "user", "content": "ping"}],
                model=model_name,
            )
            headers = chat_completion.headers
            
            print(f"- Remaining Requests today (RPD): {headers.get('x-ratelimit-remaining-requests')}")
            print(f"- Remaining Tokens this minute (TPM): {headers.get('x-ratelimit-remaining-tokens')}")
            print(f"- Total Limit Requests per day: {headers.get('x-ratelimit-limit-requests')}")
            print(f"- Total Limit Tokens per minute: {headers.get('x-ratelimit-limit-tokens')}")
            print(f"- Limit Reset Time (Tokens): {headers.get('x-ratelimit-reset-tokens')}")
        except Exception as e:
            print(f"An error occurred fetching Groq usage: {e}")

    @staticmethod
    def gemini_context_limits(model_name: str = "gemini-3.8-flash"):
        
        try:
            print(f"\n--- Gemini Limits for {model_name} ---")
            model_info = gemini_client.models.get(model=model_name)
            print(f"- Input Token Limit: {model_info.input_token_limit}")
            print(f"- Output Token Limit: {model_info.output_token_limit}")
        except Exception as e:
            print(f"An error occurred fetching Gemini limits: {e}")

    @staticmethod
    def gemini_count_tokens(text_prompt: str = "How many credits does this sentence take?", model_name: str = "gemini-3.8-flash"):
        
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