import json

import httpx
import pytest

from glucowidget.ai.providers import AIError, analyze


def capture(response_json, status=200):
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["headers"] = request.headers
        seen["body"] = json.loads(request.content)
        return httpx.Response(status, json=response_json)

    return httpx.MockTransport(handler), seen


def test_openai():
    t, seen = capture({"choices": [{"message": {"content": "ok openai"}}]})
    assert analyze("openai", "k", "gpt-x", "sys", "user", transport=t) == "ok openai"
    assert seen["url"] == "https://api.openai.com/v1/chat/completions"
    assert seen["headers"]["authorization"] == "Bearer k"
    assert seen["body"]["messages"][0] == {"role": "system", "content": "sys"}


def test_anthropic():
    t, seen = capture({"content": [{"type": "text", "text": "ok claude"}]})
    assert analyze("anthropic", "k", "", "sys", "user", transport=t) == "ok claude"
    assert seen["url"] == "https://api.anthropic.com/v1/messages"
    assert seen["headers"]["x-api-key"] == "k"
    assert seen["headers"]["anthropic-version"] == "2023-06-01"
    assert seen["body"]["system"] == "sys"
    assert seen["body"]["model"]  # usa o modelo padrão


def test_gemini():
    t, seen = capture({"candidates": [{"content": {"parts": [{"text": "ok gemini"}]}}]})
    assert analyze("gemini", "k", "gemini-x", "sys", "user", transport=t) == "ok gemini"
    assert seen["url"].endswith("/models/gemini-x:generateContent")
    assert seen["headers"]["x-goog-api-key"] == "k"
    assert seen["body"]["systemInstruction"]["parts"][0]["text"] == "sys"


def test_custom_base_url_without_key():
    t, seen = capture({"choices": [{"message": {"content": "local"}}]})
    assert analyze("ollama", "", "llama3", "s", "u", base_url="http://host:1234/v1/", transport=t) == "local"
    assert seen["url"] == "http://host:1234/v1/chat/completions"
    assert "authorization" not in seen["headers"]


def test_errors_are_friendly():
    t, _ = capture({"error": {"message": "bad key"}}, status=401)
    with pytest.raises(AIError, match="Invalid API key"):
        analyze("openai", "k", "m", "s", "u", transport=t)
    with pytest.raises(AIError, match="API key"):
        analyze("openai", "", "m", "s", "u")
