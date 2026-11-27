from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import Runnable
from configs.config import get_settings


def build_gemini_model():
    
    settings = get_settings()
    model_name = settings.GEMINI_MODEL
    api_key = (
        settings.gemini_api_key.get_secret_value()
        if settings.gemini_api_key
        else None
    )

    model = ChatGoogleGenerativeAI(
        model=model_name,
        api_key=api_key
    )

    return model
