import json
from datetime import datetime
from pathlib import Path


MEMORY_FILE = Path(__file__).with_name("memory.json")

DEFAULT_MEMORY = {
    "facts": {},
    "preferences": {},
    "state": {
        "mode": "normal",
        "llm_provider": "ollama",
        "last_app": None,
        "last_intent": None,
        "last_action": None,
        "last_query": None,
    },
    "events": [],
}


def load_memory():
    if not MEMORY_FILE.exists() or MEMORY_FILE.stat().st_size == 0:
        memory = _fresh_default()
        save_memory(memory)
        return memory

    try:
        with MEMORY_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        data = _fresh_default()

    return _merge_defaults(data)


def save_memory(memory):
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with MEMORY_FILE.open("w", encoding="utf-8") as file:
        json.dump(_merge_defaults(memory), file, indent=2)


def remember_event(user_text, decision, response=None):
    memory = load_memory()
    event = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "user": user_text,
        "intent": decision.intent,
        "action": decision.action,
        "target": decision.target,
        "response": _sanitize_response(response),
    }

    memory["events"].append(event)
    memory["events"] = memory["events"][-30:]
    memory["state"]["last_intent"] = decision.intent
    memory["state"]["last_action"] = decision.action

    if decision.target and decision.action in {
        "open_app",
        "open_file",
        "open_folder",
        "close_app",
        "open_site",
        "search_web",
        "search_youtube",
    }:
        memory["state"]["last_app"] = decision.target

    if isinstance(decision.query, str) and decision.query:
        memory["state"]["last_query"] = decision.query

    save_memory(memory)


def remember_state(key, value):
    memory = load_memory()
    memory["state"][key] = value
    save_memory(memory)


def get_llm_provider():
    provider = load_memory()["state"].get("llm_provider", "ollama")
    if provider not in {"ollama", "api"}:
        return "ollama"
    return provider


def set_llm_provider(provider):
    provider = str(provider).strip().lower()
    if provider not in {"ollama", "api"}:
        provider = "ollama"
    remember_state("llm_provider", provider)
    return provider


def remember_preference(key, value):
    memory = load_memory()
    memory["preferences"][key] = value
    save_memory(memory)


def get_context_summary(max_events=5):
    memory = load_memory()
    recent = memory["events"][-max_events:]
    lines = [
        f"Mode: {memory['state'].get('mode', 'normal')}",
        f"LLM provider: {memory['state'].get('llm_provider', 'ollama')}",
        f"Last app: {memory['state'].get('last_app') or 'none'}",
    ]

    if memory["preferences"]:
        prefs = ", ".join(f"{key}={value}" for key, value in memory["preferences"].items())
        lines.append(f"Preferences: {prefs}")

    if recent:
        lines.append("Recent events:")
        for event in recent:
            lines.append(
                f"- user={event.get('user')} intent={event.get('intent')} "
                f"action={event.get('action')} target={event.get('target')}"
            )

    return "\n".join(lines)


def _fresh_default():
    return {
        "facts": dict(DEFAULT_MEMORY["facts"]),
        "preferences": dict(DEFAULT_MEMORY["preferences"]),
        "state": dict(DEFAULT_MEMORY["state"]),
        "events": list(DEFAULT_MEMORY["events"]),
    }


def _merge_defaults(data):
    merged = _fresh_default()

    if isinstance(data, dict):
        for key in ("facts", "preferences", "state"):
            if isinstance(data.get(key), dict):
                merged[key].update(data[key])
        if isinstance(data.get("events"), list):
            merged["events"] = [_sanitize_event(event) for event in data["events"] if isinstance(event, dict)]

    return merged


def _sanitize_event(event):
    sanitized = dict(event)
    sanitized["response"] = _sanitize_response(sanitized.get("response"))
    return sanitized


def _sanitize_response(response):
    if not isinstance(response, str):
        return response

    leak_markers = (
        "MEMORY CONTEXT",
        "=== CONVERSATION ===",
        "=========================",
    )

    if any(marker in response.upper() for marker in leak_markers):
        return "AI response omitted because it contained internal context text."

    return response
