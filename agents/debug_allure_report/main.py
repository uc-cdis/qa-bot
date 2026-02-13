from agents.allure_report_debug_agent import agent_executor


def main():
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        response = agent_executor.invoke({"input": user_input})
        print("Agent:", response["output"])


if __name__ == "__main__":
    main()
