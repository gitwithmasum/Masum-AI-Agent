import asyncio
import json
import os
import urllib.error
import urllib.request
from datetime import datetime

from dotenv import load_dotenv
from agents import (
    Agent,
    AsyncOpenAI,
    OpenAIChatCompletionsModel,
    Runner,
    function_tool,
    set_tracing_disabled,
)

load_dotenv(override=True)


@function_tool
def get_current_time() -> str:
    """Return the computer's current local date and time."""
    return datetime.now().astimezone().strftime(
        "%A, %d %B %Y - %I:%M:%S %p %Z"
    )


INSTRUCTIONS = """
You are Masum AI Agent, a modular personal AI assistant.

Core responsibilities:
- Help with programming and software development.
- Help with AI, machine learning, and research.
- Explain technical topics clearly and practically.
- Use available tools when they are useful.
- Never claim that a tool was used unless it was actually used.
- Respond mainly in Bangla when the user speaks Bangla.
- Keep useful English technical terms where they improve clarity.
"""


def check_ollama(model_name: str) -> None:
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=4) as response:
            data = json.load(response)
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise RuntimeError(
            "Ollama is not reachable. Install/start Ollama first, then run "
            f"'ollama pull {model_name}'. Expected server: {host}"
        ) from error

    installed_models = {
        item.get("name") or item.get("model")
        for item in data.get("models", [])
        if item.get("name") or item.get("model")
    }

    if model_name not in installed_models:
        raise RuntimeError(
            f"Local model '{model_name}' is not installed. "
            f"Run: ollama pull {model_name}"
        )


def build_agent() -> tuple[Agent, str, str]:
    provider = os.getenv("AI_PROVIDER", "ollama").strip().lower()

    if provider == "ollama":
        model_name = os.getenv("OLLAMA_MODEL", "qwen3:4b").strip()
        base_url = os.getenv(
            "OLLAMA_BASE_URL",
            "http://localhost:11434/v1",
        ).rstrip("/")

        check_ollama(model_name)
        set_tracing_disabled(True)

        local_client = AsyncOpenAI(base_url=base_url, api_key="ollama")
        local_model = OpenAIChatCompletionsModel(
            model=model_name,
            openai_client=local_client,
        )

        agent = Agent(
            name="Masum AI Agent",
            instructions=INSTRUCTIONS,
            model=local_model,
            tools=[get_current_time],
        )
        return agent, provider, model_name

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key or "your_openai_api_key_here" in api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is missing or still contains the placeholder value."
            )

        model_name = os.getenv("OPENAI_MODEL", "").strip()
        kwargs = {
            "name": "Masum AI Agent",
            "instructions": INSTRUCTIONS,
            "tools": [get_current_time],
        }
        if model_name:
            kwargs["model"] = model_name

        agent = Agent(**kwargs)
        return agent, provider, model_name or "OpenAI SDK default"

    raise RuntimeError(
        f"Unsupported AI_PROVIDER='{provider}'. Use 'ollama' or 'openai'."
    )


async def main() -> None:
    try:
        agent, provider, model_name = build_agent()
    except RuntimeError as error:
        print(f"\n❌ Startup error: {error}\n")
        return

    print("=" * 60)
    print("🤖 MASUM AI AGENT v1.0 — LOCAL/FREE MODE")
    print(f"Provider : {provider}")
    print(f"Model    : {model_name}")
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
