from langchain.prompts import ChatPromptTemplate

agent_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a strict workflow agent.

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
""",
        ),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
)
