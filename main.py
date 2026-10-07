import asyncio
import os
from datetime import datetime

from dotenv import load_dotenv
from agents import Agent, Runner, function_tool


load_dotenv()


@function_tool
def get_current_time() -> str:
    """Return the computer's current local date and time."""
    return datetime.now().astimezone().strftime(
        "%A, %d %B %Y - %I:%M:%S %p %Z"
    )


agent = Agent(
    name="Masum AI Agent",
    instructions="""
You are Masum AI Agent, a modular personal AI assistant.

Core responsibilities:
- Help with programming and software development.
- Help with AI, machine learning, and research.
- Explain technical topics clearly and practically.
- Use available tools when they are useful.
- Never claim that a tool was used unless it was actually used.
- Respond mainly in Bangla when the user speaks Bangla.
- Keep useful English technical terms where they improve clarity.
""",
    tools=[get_current_time],
)


async def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Copy .env.example to .env and add your API key."
        )

    print("=" * 60)
    print("🤖 MASUM AI AGENT v1.0")
    print("Type 'exit' or 'quit' to close.")
    print("=" * 60)

    while True:
        user_input = input("\nMasum: ").strip()

        if user_input.lower() in {"exit", "quit"}:
            print("\nAgent: Goodbye Masum 👋")
            break

        if not user_input:
            continue

        try:
            result = await Runner.run(agent, user_input)
            print(f"\nAgent: {result.final_output}")
        except Exception as error:
            print(f"\n❌ Error: {error}")


if __name__ == "__main__":
    asyncio.run(main())
