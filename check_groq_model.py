from backend.app.config import get_settings
from groq import Groq


settings = get_settings()
# Initialize the client. 
# This automatically picks up your GROQ_API_KEY environment variable.
client = Groq(api_key=settings.groq_api_key.get_secret_value())

try:
    # Fetch the list of available models
    models_list = client.models.list()
    
    print("--- Available Groq Models ---")
    for model in models_list.data:
        print(f"- {model.id}")
        
except Exception as e:
    print(f"An error occurred: {e}")
