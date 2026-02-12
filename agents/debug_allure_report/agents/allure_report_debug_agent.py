from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_ollama import ChatOllama
from prompts.allure_debug_prompt import agent_prompt
from tools.s3_tools import (
    analyze_failed_tests,
    download_allure_files,
    find_failed_tests,
)

llm = ChatOllama(model="qwen3:4b", temperature=0)

tools = [download_allure_files, find_failed_tests, analyze_failed_tests]

agent = create_tool_calling_agent(llm, tools, agent_prompt)

agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
