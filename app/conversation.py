from __future__ import annotations

from typing import Callable

from . import config

Message = dict  # {"role": "user" | "model", "content": str}


class Conversation:
    def __init__(
        self,
        max_messages: int = config.MAX_MESSAGES,
        keep_recent: int = config.KEEP_RECENT,
    ):
        assert keep_recent < max_messages, "keep_recent must be smaller than max_messages"
        self.max_messages = max_messages
        self.keep_recent = keep_recent
        self.messages: list[Message] = []
        self.summary: str = ""

    # -- prompt building ---------------------------------------------------
    def system_prompt(self) -> str:
        if not self.summary:
            return config.SYSTEM_PROMPT
        return (
            f"{config.SYSTEM_PROMPT}\n\n"
            f"Summary of the earlier part of this conversation (older messages were trimmed):\n"
            f"{self.summary}"
        )

    # -- context management ------------------------------------------------
    def compress(self, summarizer: Callable[[str, list[Message]], str] | None) -> bool:
        """Shrink history if it is too long. Returns True if anything was dropped."""
        if len(self.messages) <= self.max_messages:
            return False

        cut = len(self.messages) - self.keep_recent
        # Keep the window starting on a user turn so roles keep alternating.
        while cut < len(self.messages) and self.messages[cut]["role"] != "user":
            cut += 1
        old, recent = self.messages[:cut], self.messages[cut:]

        if summarizer is not None:
            try:
                self.summary = summarizer(self.summary, old)
            except Exception:
                pass  # graceful fallback: plain truncation (old turns are dropped anyway)
        self.messages = recent
        return True

    # -- main entry point --------------------------------------------------
    def send(
        self,
        user_text: str,
        generate: Callable[[str, list[Message]], str],
        summarizer: Callable[[str, list[Message]], str] | None = None,
    ) -> tuple[str, bool]:
        """Add a user message, get a reply, store it. Returns (reply, was_compressed)."""
        compressed = self.compress(summarizer)
        self.messages.append({"role": "user", "content": user_text})
        try:
            reply = generate(self.system_prompt(), self.messages)
        except Exception:
            self.messages.pop()  # don't leave a dangling user turn in history
            raise
        self.messages.append({"role": "model", "content": reply})
        return reply, compressed
