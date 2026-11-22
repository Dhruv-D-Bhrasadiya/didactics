from backend.app.configs.config import Setting
from backend.app.prompts.prompt_loader import load_prompt


class SolutionAgent:
    name = "agent_1_solution_strategist"
    def run(self, problem: dict):
        setting = Setting()
        if not problem["description"].strip():
            raise ValueError("Solution agent requires a non-empty problem description.")

        system_prompt = load_prompt("solution_agent")
        user_prompt = problem

        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(model=setting.gemini_model, api_key=setting.gemini_api_key)

        response = llm.invoke([
            ("system", system_prompt),
            ("human", user_prompt),
        ])

        print(response.content)
