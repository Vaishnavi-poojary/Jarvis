import re
import json
from dataclasses import dataclass

import requests

from ai.router import choose_model
from memory.store import load_memory, remember_preference, set_llm_provider, remember_state


OLLAMA_URL = "http://localhost:11434/api/generate"
LLM_FALLBACK_THRESHOLD = 0.7
VALID_ROUTES = {"action", "ask", "chat", "multi"}
VALID_ACTIONS = {
    None,
    "ask_followup",
    "close_app",
    "open_app",
    "open_file",
    "open_folder",
    "open_site",
    "remember_preference",
    "remember_state",
    "search_web",
    "search_youtube",
}
VALID_INTENTS = {
    "chat",
    "close_app",
    "missing_input",
    "multi_step",
    "open_app",
    "open_file",
    "open_folder",
    "open_site",
    "play_media",
    "remember_preference",
    "search_web",
    "set_mode",
}
  

@dataclass
class Decision:
    route: str
    intent: str
    action: str | None = None
    target: str | None = None
    query: str | list[str] | None = None
    response: str | None = None
    confidence: float = 0.0
    should_speak: bool = True


APP_ALIASES = {
    "notepad": "notepad",
    "notes": "notepad",
    "calculator": "calculator",
    "calc": "calculator",
    "chrome": "chrome",
    "browser": "chrome",
}

SITE_ALIASES = {
    "youtube": "youtube",
    "google": "google",
    "github": "github",
    "stack overflow": "stackoverflow",
    "stackoverflow": "stackoverflow",
    "chatgpt": "chatgpt",
    "netflix": "netflix",
    "linkedin": "linkedin",
    "gmail": "gmail",
    "spotify": "spotify",
    "whatsapp": "whatsapp"
}

FOLDER_ALIASES = {
    "desktop": "desktop",
    "documents": "documents",
    "downloads": "downloads",
    "download": "downloads",
    "pictures": "pictures",
    "photos": "pictures",
    "project folder": "project_folder",
    "workspace": "project_folder",
}

BUSY_PHRASES = {"i am busy", "i'm busy", "im busy", "busy now", "do not disturb"}
NORMAL_PHRASES = {"i am free", "i'm free", "im free", "normal mode", "you can talk"}
API_PROVIDER_PHRASES = {"switch to api mode", "use api"}
OLLAMA_PROVIDER_PHRASES = {"switch to ollama mode", "use ollama"}
MEDIA_VERBS = {"watch", "play"}
YOUTUBE_FILLER_PHRASES = (
    "i want to watch",
    "i wanna watch",
    "want to watch",
    "i want to play",
    "i wanna play",
    "want to play",
    "can you play",
    "could you play",
    "please play",
    "please watch",
    "watch",
    "play",
    "open",
    "youtube",
    "please",
)
TRAILING_CONNECTORS = {"on", "in", "at", "from"}
CONTEXT_QUERY_WORDS = {"it", "again"}


def plan(command: str) -> Decision:
    text = _clean(command)
    memory = load_memory()

    if not text:
        return Decision(
            route="ask",
            intent="missing_input",
            response="I did not catch that. Please say it again.",
            confidence=1.0,
        )

    if any(phrase in text for phrase in BUSY_PHRASES):
        remember_state("mode", "busy")
        return Decision(
            route="chat",
            intent="set_mode",
            action="remember_state",
            target="busy",
            response="Understood. I will keep replies short and only interrupt for clear commands.",
            confidence=0.95,
        )

    if any(phrase in text for phrase in NORMAL_PHRASES):
        remember_state("mode", "normal")
        return Decision(
            route="chat",
            intent="set_mode",
            action="remember_state",
            target="normal",
            response="Normal mode restored.",
            confidence=0.95,
        )

    provider = _extract_provider_switch(text)
    if provider:
        set_llm_provider(provider)
        label = "API" if provider == "api" else "Ollama"
        return Decision(
            route="chat",
            intent="set_mode",
            action="remember_state",
            target=provider,
            response=f"{label} mode enabled.",
            confidence=0.95,
        )

    preference = _extract_preference(text)
    if preference:
        key, value = preference
        remember_preference(key, value)
        return Decision(
            route="chat",
            intent="remember_preference",
            action="remember_preference",
            target=key,
            query=value,
            response=f"I will remember that your {key.replace('_', ' ')} is {value}.",
            confidence=0.9,
        )

    multi_steps = _extract_multi_steps(text)
    if multi_steps:
        return Decision(
            route="multi",
            intent="multi_step",
            query=multi_steps,
            confidence=0.9,
        )

    if _is_close_command(text):
        target = _find_app(text) or memory["state"].get("last_app")
        if not target:
            return Decision(
                route="ask",
                intent="close_app",
                action="ask_followup",
                response="What should I close?",
                confidence=0.8,
            )
        return Decision(
            route="action",
            intent="close_app",
            action="close_app",
            target=target,
            confidence=0.9,
        )

    repeated_query_decision = _repeat_query_decision(text, memory)
    if repeated_query_decision:
        return repeated_query_decision

    youtube_query = _extract_youtube_query(text)
    if youtube_query is not None:
        youtube_query = _resolve_context_query(youtube_query, memory)
        if youtube_query:
            return Decision(
                route="action",
                intent="play_media",
                action="search_youtube",
                target="youtube",
                query=youtube_query,
                confidence=0.9,
            )
        if _is_media_request(text):
            return Decision(
                route="ask",
                intent="play_media",
                action="ask_followup",
                target="youtube",
                response="What would you like to watch on YouTube?",
                confidence=0.9,
            )
        return Decision(
            route="action",
            intent="open_site",
            action="open_site",
            target="youtube",
            confidence=0.85,
        )

    if _is_search_command(text):
        query = _extract_search_query(text)
        query = _resolve_context_query(query, memory)
        if not query:
            return Decision(
                route="ask",
                intent="search_web",
                action="ask_followup",
                response="What should I search?",
                confidence=0.85,
            )
        return Decision(
            route="action",
            intent="search_web",
            action="search_web",
            target="google",
            query=query,
            confidence=0.85,
        )

    site = _find_site(text)
    if site and "open" in text:
        return Decision(
            route="action",
            intent="open_site",
            action="open_site",
            target=site,
            confidence=0.85,
        )

    folder = _find_folder(text)
    if folder and _is_open_command(text):
        return Decision(
            route="action",
            intent="open_folder",
            action="open_folder",
            target=folder,
            confidence=0.9,
        )

    app = _find_app(text)
    if app and _is_app_open_command(text):
        return Decision(
            route="action",
            intent="open_app",
            action="open_app",
            target=app,
            confidence=0.85,
        )

    file_query = _extract_open_file_query(text)
    if file_query:
        return Decision(
            route="action",
            intent="open_file",
            action="open_file",
            query=file_query,
            confidence=0.85,
        )

    if _looks_like_direct_app_open(text):
        target = text.split()[-1]
        return _with_llm_fallback(
            command,
            text,
            Decision(
                route="action",
                intent="open_app",
                action="open_app",
                target=target,
                confidence=0.55,
            ),
        )

    if memory["state"].get("mode") == "busy":
        return _with_llm_fallback(
            command,
            text,
            Decision(
                route="chat",
                intent="chat",
                response="I heard you. Since you are busy, I will keep it brief.",
                confidence=0.6,
            ),
        )

    return _with_llm_fallback(
        command,
        text,
        Decision(route="chat", intent="chat", confidence=0.5),
    )


def ai_decide(command: str, cleaned_text: str | None = None) -> Decision | None:
    text = cleaned_text or _clean(command)
    prompt = _build_ai_decision_prompt(command, text)
    payload = {
        "model": choose_model(command),
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": 160,
            "temperature": 0,
        },
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=5)
        response.raise_for_status()
        raw_response = response.json().get("response", "")
    except (requests.RequestException, ValueError):
        return None

    data = _parse_ai_decision_json(raw_response)
    if not data:
        return None

    return _decision_from_ai_data(data)


def _clean(command: str) -> str:
    return " ".join(command.lower().strip().split())


def _with_llm_fallback(command: str, cleaned_text: str, decision: Decision) -> Decision:
    if decision.confidence >= LLM_FALLBACK_THRESHOLD:
        return decision

    ai_decision = ai_decide(command, cleaned_text)
    if ai_decision:
        return ai_decision

    return decision


def _build_ai_decision_prompt(command: str, cleaned_text: str) -> str:
    return f"""
You are a command planner for Jarvis. Return only one compact JSON object.
Do not include markdown, commentary, or extra keys.

Allowed routes: action, ask, chat
Allowed actions: ask_followup, close_app, open_app, open_file, open_folder, open_site, search_web, search_youtube, null
Allowed targets: notepad, calculator, chrome, youtube, google, github, stackoverflow, or null

Use action when the user clearly wants Jarvis to do something.
Use ask when the command is incomplete and needs one short follow-up question.
Use chat for ordinary conversation or questions that need a normal AI answer.

JSON shape:
{{"route":"chat","intent":"chat","action":null,"target":null,"query":null,"response":null,"confidence":0.0,"should_speak":true}}

User command: {command!r}
Cleaned command: {cleaned_text!r}
""".strip()


def _parse_ai_decision_json(raw_response: str):
    text = raw_response.strip()
    if not text:
        return None

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None

    return data if isinstance(data, dict) else None


def _decision_from_ai_data(data) -> Decision | None:
    route = data.get("route")
    intent = data.get("intent") or "chat"
    action = _none_if_blank(data.get("action"))
    target = _none_if_blank(data.get("target"))
    query = _none_if_blank(data.get("query"))
    response = _none_if_blank(data.get("response"))
    confidence = data.get("confidence", LLM_FALLBACK_THRESHOLD)
    should_speak = data.get("should_speak", True)

    if route not in VALID_ROUTES or intent not in VALID_INTENTS or action not in VALID_ACTIONS:
        return None

    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = LLM_FALLBACK_THRESHOLD

    confidence = max(0.0, min(confidence, 1.0))

    if route == "action" and action in {None, "ask_followup"}:
        return None

    if route == "ask":
        action = "ask_followup"
        response = response or "What should I do next?"

    return Decision(
        route=route,
        intent=intent,
        action=action,
        target=target,
        query=query,
        response=response,
        confidence=confidence,
        should_speak=bool(should_speak),
    )


def _none_if_blank(value):
    if not isinstance(value, str):
        return value

    value = value.strip()
    if value.lower() in {"", "none", "null"}:
        return None

    return value


def _find_app(text: str):
    for alias, app in APP_ALIASES.items():
        if _has_word_or_phrase(text, alias):
            return app
    return None


def _find_site(text: str):
    for alias, site in SITE_ALIASES.items():
        if _has_word_or_phrase(text, alias):
            return site
    return None


def _find_folder(text: str):
    for alias, folder in FOLDER_ALIASES.items():
        if _has_word_or_phrase(text, alias):
            return folder
    return None


def _is_open_command(text: str) -> bool:
    text = _strip_polite_prefix(text)
    return text.startswith("open ")


def _is_app_open_command(text: str) -> bool:
    text = _strip_polite_prefix(text)
    if not text.startswith(("open ", "start ", "launch ")):
        return False

    target = re.sub(r"^(open|start|launch)\s+", "", text).strip()
    target = re.sub(r"^(the|my)\s+", "", target).strip()
    return target in APP_ALIASES or target == "google chrome"


def _extract_open_file_query(text: str) -> str | None:
    text = _strip_polite_prefix(text)
    if not _is_open_command(text):
        return None

    query = text.removeprefix("open ").strip()
    query = re.sub(r"^(the|my)\s+", "", query).strip()
    if not query:
        return None

    return query


def _strip_polite_prefix(text: str) -> str:
    return re.sub(r"^(please|can you|could you)\s+", "", text).strip()


def _is_close_command(text: str) -> bool:
    return any(_has_word_or_phrase(text, word) for word in ("close", "exit", "quit", "stop"))


def _is_search_command(text: str) -> bool:
    return _has_word_or_phrase(text, "search") or text.startswith("google ") or "look up" in text


def _extract_provider_switch(text: str) -> str | None:
    if text in API_PROVIDER_PHRASES:
        return "api"
    if text in OLLAMA_PROVIDER_PHRASES:
        return "ollama"
    return None


def _extract_search_query(text: str) -> str:
    query = text
    for phrase in ("search for", "search", "google for", "google", "look up"):
        query = _remove_phrase(query, phrase)
    return " ".join(query.split())


def _extract_youtube_query(text: str):
    if not _is_youtube_command(text):
        return None

    query = text
    for phrase in YOUTUBE_FILLER_PHRASES:
        query = _remove_phrase(query, phrase)

    words = query.split()
    while words and words[-1] in TRAILING_CONNECTORS:
        words.pop()

    query = " ".join(words)

    if query == "":
        return ""

    return query


def _repeat_query_decision(text: str, memory) -> Decision | None:
    if not _is_context_only_query(text):
        return None

    last_query = _last_query(memory)
    if not last_query:
        return None

    last_action = memory["state"].get("last_action")
    if last_action == "search_youtube":
        return Decision(
            route="action",
            intent="play_media",
            action="search_youtube",
            target="youtube",
            query=last_query,
            confidence=0.9,
        )

    if last_action == "search_web":
        return Decision(
            route="action",
            intent="search_web",
            action="search_web",
            target="google",
            query=last_query,
            confidence=0.85,
        )

    return None


def _resolve_context_query(query: str, memory) -> str:
    if not _is_context_only_query(query):
        return query

    return _last_query(memory) or ""


def _is_context_only_query(query: str) -> bool:
    words = query.split()
    return bool(words) and all(word in CONTEXT_QUERY_WORDS for word in words)


def _last_query(memory) -> str | None:
    last_query = memory["state"].get("last_query")
    if isinstance(last_query, str) and last_query.strip():
        return last_query.strip()
    return None


def _extract_preference(text: str):
    for marker in ("remember that my ", "my "):
        if marker not in text:
            continue

        tail = text.split(marker, 1)[1]
        key, separator, value = tail.partition(" is ")
        if not separator:
            return None

        key = key.strip()
        value = value.strip()
        if key and value and len(key.split()) <= 4:
            return key.replace(" ", "_"), value
    return None


def _extract_multi_steps(text: str) -> list[str] | None:
    if not _has_word_or_phrase(text, "and"):
        return None

    steps = [step.strip() for step in re.split(r"\band\b", text) if step.strip()]
    return steps if len(steps) > 1 else None


def _looks_like_direct_app_open(text: str) -> bool:
    return text.startswith(("open ", "start ", "launch ")) and len(text.split()) <= 4


def _is_youtube_command(text: str) -> bool:
    return (
        _has_word_or_phrase(text, "youtube")
        or _has_word_or_phrase(text, "tmkoc")
        or _is_media_request(text)
    )


def _is_media_request(text: str) -> bool:
    words = set(text.split())
    return bool(words & MEDIA_VERBS) or text.startswith(("i want to watch", "i wanna watch", "i want to play"))


def _has_word_or_phrase(text: str, phrase: str) -> bool:
    return re.search(rf"\b{re.escape(phrase)}\b", text) is not None


def _remove_phrase(text: str, phrase: str) -> str:
    return re.sub(rf"\b{re.escape(phrase)}\b", " ", text)
