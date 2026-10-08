import asyncio
import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from ddgs import DDGS
from ddgs.exceptions import DDGSException
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
WEB_SEARCH_MAX_RESULTS = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "5"))
WEB_SEARCH_TIMEOUT = int(os.getenv("WEB_SEARCH_TIMEOUT", "10"))


@function_tool
def get_current_time() -> str:
    """Return the computer's current local date and time."""
    return datetime.now().astimezone().strftime(
        "%A, %d %B %Y - %I:%M:%S %p %Z"
    )


def search_web(query: str, max_results: int | None = None) -> str:
    """Run a key-free web search and return compact source results."""
    query = query.strip()
    if not query:
        return "Search query is empty."

    limit = max_results or WEB_SEARCH_MAX_RESULTS
    limit = max(1, min(limit, 8))

    try:
        results = DDGS(timeout=WEB_SEARCH_TIMEOUT).text(
            query,
            max_results=limit,
        )
    except DDGSException as error:
        return f"Web search failed: {error}"
    except Exception as error:
        return f"Web search failed unexpectedly: {error}"

    if not results:
        return f"No web results found for: {query}"

    lines = [f"Live web results for: {query}"]
    for index, item in enumerate(results, start=1):
        title = (item.get("title") or "Untitled").strip()
        url = (item.get("href") or "").strip()
        body = (item.get("body") or "").strip()

        lines.append(f"\n[{index}] {title}")
        if body:
            lines.append(body)
        if url:
            lines.append(f"Source: {url}")

    return "\n".join(lines)


@function_tool
def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the live public web.

    Use this for current information, recent events, documentation,
    changing facts, websites, products, releases, or anything that
    may require up-to-date information. Return sources with the result.
    """
    return search_web(query, max_results=max_results)


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
- For current, latest, recent, changing, or web-specific information, use web_search.
- When using web_search, mention useful source URLs in the final answer.
- Do not invent search results or sources.
"""

LOCAL_FAST_INSTRUCTIONS = INSTRUCTIONS + """
- You are running on a small local model. Prefer short, direct answers.
- For simple tool requests, call the required tool immediately without lengthy reasoning.
- If the user asks for the current date or time, call get_current_time immediately.
- If the user asks to search the web, find current information, or asks for latest/recent information, call web_search immediately.
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
    tools = [get_current_time, web_search]

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
            tools=tools,
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
            "tools": tools,
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


async def run_direct_search(query: str) -> None:
    if not query:
        print("\nUsage: /search <your query>")
        return

    print("\n🌐 Searching the web...")
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(search_web, query),
            timeout=WEB_SEARCH_TIMEOUT + 10,
        )
        print(f"\n{result}")
    except asyncio.TimeoutError:
        print("\n⏱️ Web search timed out. Try again with a shorter query.")


async def main() -> None:
    try:
        agent, provider, model_name = build_agent()
        session = build_memory_session()
    except RuntimeError as error:
        print(f"\n❌ Startup error: {error}\n")
        return

    print("=" * 60)
    print("🤖 MASUM AI AGENT v1.2 — MEMORY + WEB SEARCH")
    print(f"Provider : {provider}")
    print(f"Model    : {model_name}")
    if provider == "ollama":
        print("Fast mode: enabled")
    print(f"Memory   : {MEMORY_SESSION_ID}")
    print(f"Database : {MEMORY_DB_PATH}")
    print(f"Web      : enabled ({WEB_SEARCH_MAX_RESULTS} results)")
    print(f"Timeout  : {AGENT_TIMEOUT_SECONDS}s")
    print("Commands : /search <query>, /memory, /clear-memory, exit")
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

        if user_input.lower().startswith("/search"):
            query = user_input[len("/search"):].strip()
            await run_direct_search(query)
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
                "Try a shorter prompt or use /search for direct web results."
            )
        except Exception as error:
            print(f"\n❌ Error: {error}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nAgent stopped cleanly. 👋")
