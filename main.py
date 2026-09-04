import json
import os
from backend.app.agents.intent_analyzer_agent import create_intent_analyzer_agent

# 1. Define configuration
provider = "groq"
model_name = "qwen/qwen3.8-27b"
agent_name = "intent_analyzer_agent"

# 2. Initialize agent
agent = create_intent_analyzer_agent(provider=provider, model_name=model_name)

# 3. Get the JSON output string
output_json = agent.analyze("Teach me binary search in Java.").model_dump_json(indent=2)
print(output_json)

# 4. Sanitize the model name for the file system
safe_model_name = model_name.replace("/", "_").replace("-", "_").replace(".", "_")
file_name = f"{provider}_{safe_model_name}.json"

# 5. Build the structured path: debug/{agent_name}/
output_dir = os.path.join("debug", agent_name)
os.makedirs(output_dir, exist_ok=True)  # Creates both 'debug' and the subfolder if they don't exist

# 6. Save the file
file_path = os.path.join(output_dir, file_name)
with open(file_path, "w", encoding="utf-8") as f:
    f.write(output_json)

print(f"\n[SUCCESS] Output successfully saved to: {file_path}")