from __future__ import annotations

AGENT_DESCRIPTIONS = {
    "general": (
        "General Coordinator — mixed questions, planning, explanations, "
        "and requests that do not belong to one specialist."
    ),
    "research": (
        "Research Agent — papers, thesis, literature review, web evidence, "
        "research methods, datasets, and research synthesis."
    ),
    "developer": (
        "Developer Agent — programming, debugging, GitHub, repository code, "
        "issues, commits, architecture, and deployment reasoning."
    ),
    "gmail": (
        "Gmail Agent — read-only inbox search, message reading, and summaries."
    ),
    "data": (
        "Data Agent — read-only Supabase tables, rows, filters, and analysis."
    ),
}

ALIASES = {
    "general": "general",
    "coordinator": "general",
    "main": "general",
    "research": "research",
    "researcher": "research",
    "paper": "research",
    "developer": "developer",
    "dev": "developer",
    "code": "developer",
    "github": "developer",
    "gmail": "gmail",
    "email": "gmail",
    "mail": "gmail",
    "data": "data",
    "database": "data",
    "db": "data",
    "supabase": "data",
}

KEYWORDS = {
    "research": (
        "research",
        "paper",
        "papers",
        "thesis",
        "literature",
        "citation",
        "doi",
        "dataset",
        "methodology",
        "hypothesis",
        "openalex",
        "academic",
        "গবেষণা",
        "রিসার্চ",
        "পেপার",
        "থিসিস",
    ),
    "developer": (
        "github",
        "repo",
        "repository",
        "commit",
        "issue",
        "code",
        "coding",
        "programming",
        "python",
        "javascript",
        "typescript",
        "react",
        "bug",
        "debug",
        "deploy",
        "deployment",
        "vercel",
        "api",
        "function",
        "class",
        "git",
        "কোড",
        "প্রোগ্রামিং",
        "গিটহাব",
    ),
    "gmail": (
        "gmail",
        "email",
        "e-mail",
        "inbox",
        "unread",
        "message",
        "mail",
        "মেইল",
        "ইমেইল",
        "ইনবক্স",
    ),
    "data": (
        "supabase",
        "database",
        "db",
        "table",
        "rows",
        "row",
        "schema",
        "sql",
        "rls",
        "ডাটাবেস",
        "টেবিল",
    ),
}


def normalize_agent_name(name: str) -> str:
    key = name.strip().lower()
    return ALIASES.get(key, key)


def _score(prompt: str, agent_name: str) -> int:
    text = prompt.lower()
    score = 0

    for keyword in KEYWORDS.get(agent_name, ()):
        if keyword in text:
            score += 1

    if agent_name == "gmail" and "gmail" in text:
        score += 3
    if agent_name == "developer" and "github" in text:
        score += 3
    if agent_name == "data" and "supabase" in text:
        score += 3
    if agent_name == "research" and (
        "research paper" in text
        or "literature review" in text
        or "thesis" in text
    ):
        score += 3

    return score


def route_agent_names(
    prompt: str,
    max_agents: int = 1,
) -> list[str]:
    max_agents = max(1, min(int(max_agents), 3))

    ranked = []
    for name in ("research", "developer", "gmail", "data"):
        score = _score(prompt, name)
        if score > 0:
            ranked.append((score, name))

    ranked.sort(key=lambda item: (-item[0], item[1]))

    if not ranked:
        return ["general"]

    return [name for _, name in ranked[:max_agents]]


def format_agent_catalog() -> str:
    lines = ["Available specialist agents:"]
    for name, description in AGENT_DESCRIPTIONS.items():
        lines.append(f"- {name}: {description}")
    return "\n".join(lines)
