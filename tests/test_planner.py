from pathlib import Path

from brain.planner import Decision, plan
import brain.planner as planner
import executor.executor as executor
import memory.store as memory_store


def test_open_calculator():
    d = plan("open calculator")
    assert d.route == "action"
    assert d.action == "open_app"


def test_open_downloads_folder():
    d = plan("open downloads")
    assert d.route == "action"
    assert d.action == "open_folder"
    assert d.target == "downloads"


def test_open_file_query():
    d = plan("open resume")
    assert d.route == "action"
    assert d.intent == "open_file"
    assert d.action == "open_file"
    assert d.query == "resume"


def test_open_notes_with_descriptor_is_file_not_notepad():
    d = plan("open dbms notes")
    assert d.action == "open_file"
    assert d.query == "dbms notes"


def test_open_notes_alone_still_opens_app():
    d = plan("open notes")
    assert d.action == "open_app"
    assert d.target == "notepad"


def test_open_website_still_wins_over_file():
    d = plan("open youtube")
    assert d.action == "open_site"
    assert d.target == "youtube"


def test_youtube_query():
    d = plan("i want to watch tmkoc in youtube")
    assert d.action == "search_youtube"
    assert "tmkoc" in (d.query or "")


def test_incomplete_watch():
    d = plan("i want to watch")
    assert d.route == "ask"


def test_search():
    d = plan("search python decorators")
    assert d.action == "search_web"


def test_memory_preference():
    d = plan("remember that my favorite show is tmkoc")
    assert d.action == "remember_preference"


def test_switch_to_api_mode_persists(monkeypatch):
    memory_file = Path(__file__).with_name(".memory_provider_test.json")
    if memory_file.exists():
        memory_file.unlink()

    monkeypatch.setattr(memory_store, "MEMORY_FILE", memory_file)

    try:
        d = plan("switch to api mode")
        memory = memory_store.load_memory()
        assert d.action == "remember_state"
        assert d.target == "api"
        assert memory["state"]["llm_provider"] == "api"
    finally:
        if memory_file.exists():
            memory_file.unlink()


def test_switch_to_ollama_mode_persists(monkeypatch):
    memory_file = Path(__file__).with_name(".memory_provider_test.json")
    if memory_file.exists():
        memory_file.unlink()

    monkeypatch.setattr(memory_store, "MEMORY_FILE", memory_file)

    try:
        d = plan("use ollama")
        memory = memory_store.load_memory()
        assert d.action == "remember_state"
        assert d.target == "ollama"
        assert memory["state"]["llm_provider"] == "ollama"
    finally:
        if memory_file.exists():
            memory_file.unlink()


def test_llm_fallback_trigger():
    d = plan("i feel bored")
    # should not crash and should return something valid
    assert d.route in {"action", "chat", "ask"}


def test_youtube_context_it(monkeypatch):
    monkeypatch.setattr(planner, "load_memory", lambda: {
        "state": {
            "mode": "normal",
            "last_action": "search_youtube",
            "last_query": "ishq bulava song",
        }
    })

    d = plan("play it again")
    assert d.action == "search_youtube"
    assert d.query == "ishq bulava song"


def test_search_context_again(monkeypatch):
    monkeypatch.setattr(planner, "load_memory", lambda: {
        "state": {
            "mode": "normal",
            "last_action": "search_web",
            "last_query": "python decorators",
        }
    })

    d = plan("again")
    assert d.action == "search_web"
    assert d.query == "python decorators"


def test_context_without_last_query_still_asks(monkeypatch):
    monkeypatch.setattr(planner, "load_memory", lambda: {
        "state": {
            "mode": "normal",
            "last_action": "search_youtube",
            "last_query": None,
        }
    })

    d = plan("play it")
    assert d.route == "ask"


def test_multi_step_search_and_open(monkeypatch):
    calls = []
    memory_events = []

    monkeypatch.setattr(executor, "search_google", lambda query: calls.append(("search_google", query)))
    monkeypatch.setattr(executor, "open_github", lambda: calls.append(("open_github", None)))
    monkeypatch.setattr(
        memory_store,
        "remember_event",
        lambda step, decision, response=None: memory_events.append((step, decision.action, response)),
    )

    d = plan("search python and open github")

    assert d.route == "multi"
    assert d.intent == "multi_step"
    assert d.query == ["search python", "open github"]

    response = executor.execute_plan(d)

    assert calls == [("search_google", "python"), ("open_github", None)]
    assert memory_events == [
        ("search python", "search_web", "Searching for python"),
        ("open github", "open_site", "Opening github"),
    ]
    assert response == "Searching for python | Opening github"


def test_multi_step_parent_does_not_overwrite_last_query(monkeypatch):
    memory_file = Path(__file__).with_name(".memory_test.json")
    if memory_file.exists():
        memory_file.unlink()

    monkeypatch.setattr(memory_store, "MEMORY_FILE", memory_file)

    try:
        memory_store.remember_event(
            "search python and open github",
            Decision(route="multi", intent="multi_step", query=["search python", "open github"]),
            "Searching for python | Opening github",
        )

        memory = memory_store.load_memory()
        assert memory["state"]["last_query"] is None
    finally:
        if memory_file.exists():
            memory_file.unlink()
