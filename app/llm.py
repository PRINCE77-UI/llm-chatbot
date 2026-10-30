from __future__ import annotations

from google import genai
from google.genai import errors, types

from . import config

_client: genai.Client | None = None


class LLMError(Exception):
    """An error whose message is safe to show directly to the end user."""

    def __init__(self, user_message: str, status: int = 502):
        super().__init__(user_message)
        self.user_message = user_message
        self.status = status


def _get_client() -> genai.Client:
    global _client
    if not config.GEMINI_API_KEY:
        raise LLMError(
            "The server has no API key configured. Set GEMINI_API_KEY in your .env file.", 500
        )
    if _client is None:
        _client = genai.Client(
            api_key=config.GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=int(config.REQUEST_TIMEOUT_S * 1000)),
        )
    return _client


def _call(system: str, messages: list[dict], temperature: float) -> str:
    contents = [
        types.Content(role=m["role"], parts=[types.Part(text=m["content"])]) for m in messages
    ]
    try:
        resp = _get_client().models.generate_content(
            model=config.GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(system_instruction=system, temperature=temperature),
        )
    except LLMError:
        raise
    except errors.APIError as e:
        code = getattr(e, "code", None)
        if code == 429:
            raise LLMError("The model is rate-limited right now. Wait a few seconds and try again.", 429)
        if code in (401, 403):
            raise LLMError("The API key was rejected. Check GEMINI_API_KEY on the server.", 500)
        if code in (400, 404):
            raise LLMError("The request was rejected by the model API. Check GEMINI_MODEL.", 502)
        raise LLMError("The model service had a problem. Please try again in a moment.", 502)
    except Exception as e:  # network down, DNS, timeout, etc.
        name = type(e).__name__.lower()
        if "timeout" in name or "timeout" in str(e).lower():
            raise LLMError("The model took too long to respond. Please try again.", 504)
        raise LLMError("Could not reach the model service. Check your connection and retry.", 503)

    text = (getattr(resp, "text", None) or "").strip()
    if not text:  # empty candidates, safety block, etc.
        raise LLMError("The model returned an empty reply. Try rephrasing your message.", 502)
    return text


def generate(system: str, messages: list[dict]) -> str:
    """Send the system prompt + message history and return the assistant's reply."""
    return _call(system, messages, temperature=0.7)


def summarize(previous_summary: str, old_messages: list[dict]) -> str:
    """Fold older messages into the running summary."""
    transcript = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in old_messages)
    prompt = (
        f"PREVIOUS SUMMARY:\n{previous_summary or '(none)'}\n\nNEW MESSAGES:\n{transcript}"
    )
    return _call(config.SUMMARY_PROMPT, [{"role": "user", "content": prompt}], temperature=0.2)
