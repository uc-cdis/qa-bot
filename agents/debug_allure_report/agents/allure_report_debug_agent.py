from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from tools.s3_tools import (
    analyze_failed_tests,
    download_allure_files,
    find_failed_tests,
)

SYSTEM_PROMPT = """You are a strict workflow agent.

You MUST follow this exact sequence:

Step 1 → Call download_allure_files
Step 2 → Call find_failed_tests
Step 3 → Call analyze_failed_tests
Step 4 → Provide final answer

Rules:
- Never skip a step.
- Never repeat a step.
- Never call a tool more than once.
- Always move to the next step after a tool succeeds.
"""

llm = ChatOllama(model="qwen3:4b", temperature=0, base_url="http://locahost:11434")

tools = [download_allure_files, find_failed_tests, analyze_failed_tests]

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
)
