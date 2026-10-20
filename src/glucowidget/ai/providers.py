"""Provedores de IA via REST (sem SDKs), usando a chave do próprio usuário."""
from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class ProviderInfo:
    id: str
    name: str
    kind: str  # openai | anthropic | gemini
    base_url: str
    default_model: str
    models: tuple[str, ...] = ()
    needs_key: bool = True
    key_url: str = ""


PROVIDERS: dict[str, ProviderInfo] = {
    p.id: p
    for p in (
        ProviderInfo("openai", "OpenAI", "openai", "https://api.openai.com/v1", "gpt-4o-mini",
                     ("gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"),
                     key_url="https://platform.openai.com/api-keys"),
        ProviderInfo("anthropic", "Anthropic Claude", "anthropic", "https://api.anthropic.com/v1", "claude-sonnet-5-5",
                     ("claude-sonnet-5-5", "claude-haiku-5-5", "claude-opus-5-5"),
                     key_url="https://console.anthropic.com/settings/keys"),
        ProviderInfo("gemini", "Google Gemini", "gemini", "https://generativelanguage.googleapis.com/v1beta",
                     "gemini-2.5-flash", ("gemini-2.5-flash", "gemini-2.5-pro"),
                     key_url="https://aistudio.google.com/apikey"),
        ProviderInfo("openrouter", "OpenRouter", "openai", "https://openrouter.ai/api/v1", "openai/gpt-4o-mini",
                     key_url="https://openrouter.ai/keys"),
        ProviderInfo("groq", "Groq", "openai", "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile",
                     key_url="https://console.groq.com/keys"),
        ProviderInfo("deepseek", "DeepSeek", "openai", "https://api.deepseek.com/v1", "deepseek-chat",
                     key_url="https://platform.deepseek.com/api_keys"),
        ProviderInfo("mistral", "Mistral", "openai", "https://api.mistral.ai/v1", "mistral-small-latest",
                     key_url="https://console.mistral.ai/api-keys"),
        ProviderInfo("ollama", "Ollama (local)", "openai", "http://localhost:11434/v1", "llama3.1", needs_key=False),
        ProviderInfo("custom", "Outro (compatível com OpenAI)", "openai", "", "", needs_key=False),
    )
}


class AIError(Exception):
    pass


def _friendly_http_error(resp: httpx.Response) -> AIError:
    detail = ""
    try:
        body = resp.json()
        err = body.get("error") if isinstance(body, dict) else None
        if isinstance(err, dict):
            detail = err.get("message", "")
        elif isinstance(err, str):
            detail = err
    except ValueError:
        detail = resp.text[:200]
    code = resp.status_code
    if code in (401, 403):
        msg = "Chave de API inválida ou sem permissão."
    elif code == 404:
        msg = "Modelo ou endpoint não encontrado. Confira o nome do modelo."
    elif code == 429:
        msg = "Limite de uso ou créditos esgotados no provedor."
    elif code >= 500:
        msg = "O provedor de IA está instável no momento."
    else:
        msg = f"Erro do provedor (HTTP {code})."
    return AIError(f"{msg}\n{detail}".strip())


def analyze(
    provider_id: str,
    api_key: str,
    model: str,
    system: str,
    user: str,
    base_url: str = "",
    timeout: float = 90.0,
    transport: httpx.BaseTransport | None = None,
) -> str:
    info = PROVIDERS.get(provider_id)
    if not info:
        raise AIError("Provedor de IA desconhecido.")
    model = model or info.default_model
    base = (base_url or info.base_url).rstrip("/")
    if not base:
        raise AIError("Informe a URL base do provedor.")
    if not model:
        raise AIError("Informe o modelo.")
    if info.needs_key and not api_key:
        raise AIError("Informe a chave de API nas configurações.")

    if info.kind == "anthropic":
        url = f"{base}/messages"
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
        body = {"model": model, "max_tokens": 1500, "system": system,
                "messages": [{"role": "user", "content": user}]}
    elif info.kind == "gemini":
        url = f"{base}/models/{model}:generateContent"
        headers = {"x-goog-api-key": api_key}
        body = {"systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}]}
    else:
        url = f"{base}/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        body = {"model": model, "messages": [{"role": "system", "content": system},
                                             {"role": "user", "content": user}]}

    try:
        with httpx.Client(transport=transport, timeout=timeout) as http:
            resp = http.post(url, headers=headers, json=body)
    except httpx.HTTPError as exc:
        raise AIError(f"Falha de conexão com o provedor de IA: {exc}") from exc
    if resp.status_code >= 400:
        raise _friendly_http_error(resp)

    try:
        data = resp.json()
        if info.kind == "anthropic":
            text = "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
        elif info.kind == "gemini":
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts)
        else:
            text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise AIError("Resposta inesperada do provedor de IA.") from exc
    if not text.strip():
        raise AIError("O provedor de IA retornou uma resposta vazia.")
    return text.strip()
