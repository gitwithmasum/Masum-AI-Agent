import asyncio
import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from agents import (
    Agent,
    AsyncOpenAI,
    OpenAIChatCompletionsModel,
    Runner,
    SQLiteSession,
    function_tool,
    set_tracing_disabled,
)

load_dotenv(override=True)

AGENT_TIMEOUT_SECONDS = int(os.getenv("AGENT_TIMEOUT_SECONDS", "120"))
MEMORY_SESSION_ID = os.getenv("MEMORY_SESSION_ID", "masum-main").strip()
MEMORY_DB_PATH = Path(os.getenv("MEMORY_DB_PATH", "data/memory.db"))


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
- Use conversation memory naturally when it is relevant.
"""

LOCAL_FAST_INSTRUCTIONS = INSTRUCTIONS + """
- You are running on a small local model. Prefer short, direct answers.
- For simple tool requests, call the required tool immediately without lengthy reasoning.
- If the user asks for the current date or time, call get_current_time immediately.
/no_think
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
        model_name = os.getenv("OLLAMA_MODEL", "qwen3:1.7b").strip()
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
            instructions=LOCAL_FAST_INSTRUCTIONS,
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


def build_memory_session() -> SQLiteSession:
    MEMORY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return SQLiteSession(
        MEMORY_SESSION_ID,
        str(MEMORY_DB_PATH),
    )


async def print_memory_info(session: SQLiteSession) -> None:
    items = await session.get_items()
    print(f"\n🧠 Memory session : {MEMORY_SESSION_ID}")
    print(f"🗄️ Memory database: {MEMORY_DB_PATH}")
    print(f"💬 Stored items   : {len(items)}")


async def main() -> None:
    try:
        agent, provider, model_name = build_agent()
        session = build_memory_session()
    except RuntimeError as error:
        print(f"\n❌ Startup error: {error}\n")
        return

    print("=" * 60)
    print("🤖 MASUM AI AGENT v1.1 — PERSISTENT MEMORY")
    print(f"Provider : {provider}")
    print(f"Model    : {model_name}")
    if provider == "ollama":
        print("Fast mode: enabled")
    print(f"Memory   : {MEMORY_SESSION_ID}")
    print(f"Database : {MEMORY_DB_PATH}")
    print(f"Timeout  : {AGENT_TIMEOUT_SECONDS}s")
    print("Commands : /memory, /clear-memory, exit")
    print("=" * 60)

    while True:
        user_input = input("\nMasum: ").strip()

        if user_input.lower() in {"exit", "quit"}:
            print("\nAgent: Goodbye Masum 👋")
            break

        if user_input.lower() == "/memory":
            await print_memory_info(session)
            continue

        if user_input.lower() == "/clear-memory":
            await session.clear_session()
            print("\n🧠 Conversation memory cleared.")
            continue

        if not user_input:
            continue

        try:
            result = await asyncio.wait_for(
                Runner.run(
                    agent,
                    user_input,
                    session=session,
                ),
                timeout=AGENT_TIMEOUT_SECONDS,
            )
            print(f"\nAgent: {result.final_output}")
        except asyncio.TimeoutError:
            print(
                "\n⏱️ Response timed out. The local model is taking too long. "
                "Try a shorter prompt or a faster/smaller model."
            )
        except Exception as error:
            print(f"\n❌ Error: {error}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nAgent stopped cleanly. 👋")
