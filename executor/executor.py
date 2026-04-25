from tools.system_tools import (
    open_notepad, close_notepad,
    open_calculator, close_calculator,
    open_chrome, close_chrome
)

from tools.browser_tools import (
    search_google, search_youtube,
    open_github, open_stackoverflow,open_youtube
)

import os
import re

# 🔥 memory
last_app = None


def try_open_app(command: str):
    words = command.split()

    if "open" in words:
        try:
            app_name = words[-1]  # last word
            os.system(f"start {app_name}")
            return f"Trying to open {app_name}"
        except:
            return "Couldn't open that application"

    return None


def execute_command(command: str):
    global last_app

    command = command.lower()
    print("DEBUG COMMAND:", command)

    # ---- BASIC ----
    if "hello" in command:
        return "Hello, how can I help you?"

    # ---- CLOSE ----
    elif "close" in command:
        if "notepad" in command:
            close_notepad()
            return "Closing Notepad"

        elif "calculator" in command:
            close_calculator()
            return "Closing Calculator"

        elif "chrome" in command or "browser" in command:
            close_chrome()
            return "Closing Browser"

        # fallback memory
        elif last_app == "notepad":
            close_notepad()
            return "Closing Notepad"

        elif last_app == "calculator":
            close_calculator()
            return "Closing Calculator"

        elif last_app == "chrome":
            close_chrome()
            return "Closing Browser"

        return "Nothing to close"

    # ---- GOOGLE SEARCH ----
    elif "search" in command or "google" in command:
        query = _clean_query(command, ["search for", "search", "google for", "google"])

        if query == "":
            return "What should I search?"

        search_google(query)
        return f"Searching for {query}"

    # ---- OPEN APPS ----
    elif "notepad" in command:
        last_app = "notepad"
        open_notepad()
        return "Opening Notepad"

    elif "calculator" in command or "calc" in command:
        last_app = "calculator"
        open_calculator()
        return "Opening Calculator"

    elif "chrome" in command or "browser" in command:
        last_app = "chrome"
        open_chrome()
        return "Opening Browser"

    elif "youtube" in command:
        query = _clean_query(
            command,
            [
                "i want to watch",
                "i wanna watch",
                "want to watch",
                "watch",
                "open",
                "youtube",
                "play",
                "please",
            ],
        )
        query = _strip_trailing_connectors(query)

        if query:
            search_youtube(query)
            return f"Playing {query} on YouTube"
        else:
            open_youtube()
            return "Opening YouTube"
    elif "github" in command:
        open_github()
        return "Opening GitHub"

    elif "stackoverflow" in command:
        open_stackoverflow()
        return "Opening Stack Overflow"

    # 🔥 FALLBACK (THIS WAS YOUR BUG LOCATION)
    result = try_open_app(command)
    if result:
        return result

    return "Command not recognized"


def execute_plan(decision, allow_multi=True):
    global last_app

    if decision.route == "multi":
        if not allow_multi:
            return "I could not safely execute nested multi-step commands."
        return _execute_multi_plan(decision)

    action = decision.action
    target = decision.target
    query = decision.query

    if decision.response and decision.route != "action":
        return decision.response

    if action == "ask_followup":
        return decision.response or "What should I do next?"

    if action == "search_web":
        if not query:
            return "What should I search?"
        search_google(query)
        last_app = "google"
        return f"Searching for {query}"

    if action == "search_youtube":
        if not query:
            open_youtube()
            last_app = "youtube"
            return "Opening YouTube"
        search_youtube(query)
        last_app = "youtube"
        return f"Playing {query} on YouTube"

    if action == "open_site":
        if target == "youtube":
            open_youtube()
        elif target == "github":
            open_github()
        elif target == "stackoverflow":
            open_stackoverflow()
        elif target == "google":
            search_google("")
        else:
            return "I do not know that website yet"

        last_app = target
        return f"Opening {target}"

    if action == "open_app":
        if target == "notepad":
            open_notepad()
            last_app = target
            return "Opening Notepad"
        if target == "calculator":
            open_calculator()
            last_app = target
            return "Opening Calculator"
        if target == "chrome":
            open_chrome()
            last_app = target
            return "Opening Browser"

        result = try_open_app(f"open {target}")
        if result:
            last_app = target
            return result

    if action == "close_app":
        if target == "notepad":
            close_notepad()
            return "Closing Notepad"
        if target == "calculator":
            close_calculator()
            return "Closing Calculator"
        if target in {"chrome", "browser", "google", "youtube"}:
            close_chrome()
            return "Closing Browser"
        return "I do not know how to close that yet"

    return execute_command(query or target or "")


def _execute_multi_plan(decision):
    if not isinstance(decision.query, list):
        return "I could not understand the steps."

    from brain.planner import plan
    from memory.store import remember_event

    responses = []
    for step in decision.query:
        if not isinstance(step, str) or not step.strip():
            continue

        step_decision = plan(step)
        response = execute_plan(step_decision, allow_multi=False)
        remember_event(step, step_decision, response)
        responses.append(response)

    return " | ".join(responses) if responses else "I could not understand the steps."


def _clean_query(text, phrases):
    query = text
    for phrase in phrases:
        query = re.sub(rf"\b{re.escape(phrase)}\b", " ", query)
    return " ".join(query.split())


def _strip_trailing_connectors(text):
    words = text.split()
    while words and words[-1] in {"on", "in", "at", "from"}:
        words.pop()
    return " ".join(words)
