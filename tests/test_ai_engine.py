import requests

import ai.ai_engine as ai_engine


class FakeResponse:
    def __init__(self, text):
        self._text = text

    def raise_for_status(self):
        return None

    def json(self):
        return {"response": self._text}


def test_ai_response_retries_fast_model_after_timeout(monkeypatch):
    calls = []

    monkeypatch.setattr(ai_engine, "choose_model", lambda prompt: "llama3")
    monkeypatch.setattr(ai_engine, "get_context_summary", lambda: "Mode: normal")

    def fake_post(url, json, timeout):
        calls.append((json["model"], timeout))
        if json["model"] == "llama3":
            raise requests.exceptions.Timeout()
        return FakeResponse("fallback works")

    monkeypatch.setattr(ai_engine.requests, "post", fake_post)

    assert ai_engine.get_ai_response("explain python") == "fallback works"
    assert calls == [("llama3", 35), ("phi3", 25)]


def test_ai_response_returns_connection_message(monkeypatch):
    monkeypatch.setattr(ai_engine, "choose_model", lambda prompt: "phi3")
    monkeypatch.setattr(ai_engine, "get_context_summary", lambda: "Mode: normal")
    monkeypatch.setattr(
        ai_engine.requests,
        "post",
        lambda url, json, timeout: (_ for _ in ()).throw(requests.exceptions.ConnectionError()),
    )

    assert "Ollama is not running" in ai_engine.get_ai_response("hello")
