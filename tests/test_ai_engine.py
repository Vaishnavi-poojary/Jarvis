import requests

import ai.ai_engine as ai_engine


class FakeResponse:
    def __init__(self, text):
        self._text = text

    def raise_for_status(self):
        return None

    def json(self):
        return {"response": self._text}


def test_ai_response_returns_timeout_message(monkeypatch):
    calls = []

    monkeypatch.setattr(ai_engine, "choose_model", lambda prompt: "llama3")
    monkeypatch.setattr(ai_engine, "get_llm_provider", lambda: "ollama")
    monkeypatch.setattr(ai_engine, "get_context_summary", lambda: "Mode: normal")

    def fake_post(url, json, timeout):
        calls.append((json["model"], timeout))
        raise requests.exceptions.Timeout()

    monkeypatch.setattr(ai_engine.requests, "post", fake_post)

    assert ai_engine.get_ai_response("explain python") == "AI is taking too long to respond"
    assert calls == [("llama3", 60)]


def test_ai_response_returns_connection_message(monkeypatch):
    monkeypatch.setattr(ai_engine, "choose_model", lambda prompt: "phi3")
    monkeypatch.setattr(ai_engine, "get_llm_provider", lambda: "ollama")
    monkeypatch.setattr(ai_engine, "get_context_summary", lambda: "Mode: normal")
    monkeypatch.setattr(
        ai_engine.requests,
        "post",
        lambda url, json, timeout: (_ for _ in ()).throw(requests.exceptions.ConnectionError()),
    )

    assert "Ollama is not running" in ai_engine.get_ai_response("hello")


def test_api_mode_without_key_returns_configuration_message(monkeypatch):
    monkeypatch.setattr(ai_engine, "get_llm_provider", lambda: "api")
    monkeypatch.setattr(ai_engine, "load_dotenv", lambda: False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert ai_engine.get_ai_response("hello") == "API mode is enabled but no API key is configured yet."


def test_api_response_uses_openai_key_from_env(monkeypatch):
    calls = []

    class FakeApiResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {"message": {"content": "Hello from API"}},
                ],
            }

    def fake_post(url, json, headers, timeout):
        calls.append((url, json["model"], headers["Authorization"], timeout))
        return FakeApiResponse()

    monkeypatch.setattr(ai_engine, "load_dotenv", lambda: True)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ai_engine.requests, "post", fake_post)

    assert ai_engine.get_api_response("Prompt") == "Hello from API"
    assert calls == [
        (ai_engine.OPENAI_CHAT_URL, ai_engine.API_MODEL, "Bearer test-key", 60),
    ]
