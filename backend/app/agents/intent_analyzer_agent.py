from langchain_google_genai import ChatGoogleGenerativeAI 
from backend.app.config import get_settings 
from backend.app.prompts import load_prompt 

settings = get_settings()

# Error categories that trigger key rotation
# These are string fragments matched against exception messages.
# When any of these appear, we rotate to the next key instead of crashing.
ROTATABLE_ERROR_KEYWORDS = [
    "quota",
    "rate",
    "limit",
    "429",
    "exhausted",
    "resource_exhausted",
    "invalid api key",
    "authentication",
    "api key not valid",
    "permission denied",
    "403",
    "401",
    "timeout",
    "connection",
    "unavailable",
    "service unavailable",
    "503",
]

def _is_rotatable_error(exc: Exception) -> bool:
    """
        Returns True if the exception is a known rate-limit or auth error that should trigger key rotation rather than immediately crashing.
    """

    msg = str(exc).lower()
    return any(keyword in msg for keyword in ROTATABLE_ERROR_KEYWORDS)

def _build_gemini_llm(api_key: str, model_name: str):
    """Creates a ChatGoogleGenerativeAI instance with the given key."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0.2,
        max_retries=1,  # We handle retries ourselves via key rotation
    )


def _build_groq_llm(api_key: str, model_name: str):
    """Creates a ChatGroq instance with the given key."""
    from langchain_groq import ChatGroq
    return ChatGroq(
        model=model_name,
        groq_api_key=api_key,
        temperature=0.2,
        max_retries=1,
    )


class IntentAnalyzerAgent: 
    def __init__(self): 
        # Added quotes around the file path string
        self.system_template = load_prompt("prompts/intent_analyzer_agent.yaml") 
        
    def generate_system_message(self, topic: str) -> str: 
        # Fixed formatting list structure to standard string representation
        return self.system_template.format( 
            domain=topic, 
            citation_format="[Author, Date]" 
        ) 
