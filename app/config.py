import os

from dotenv import load_dotenv

load_dotenv()  # reads .env if present (it is git-ignored)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Context window management
MAX_MESSAGES = int(os.getenv("MAX_MESSAGES", "12"))   # trigger compression above this
KEEP_RECENT = int(os.getenv("KEEP_RECENT", "6"))      # always keep this many verbatim

REQUEST_TIMEOUT_S = float(os.getenv("REQUEST_TIMEOUT_S", "30"))
MAX_USER_CHARS = 4000

SYSTEM_PROMPT = """You are Byte, a friendly programming mentor for beginner and intermediate developers.

Purpose:
- Help people understand code, debug problems, and learn concepts.
- Prefer teaching over just handing over answers: explain the "why", then show a short example.

Style:
- Warm, encouraging, and concise (usually under 200 words unless the user asks for depth).
- Use code blocks for code. Ask one clarifying question when a request is ambiguous.
- If you are unsure, say so instead of guessing.

Boundaries:
- Stay on programming, software tools, and learning-to-code topics. For anything unrelated,
  politely steer back in one sentence.
- Never claim to have run code. Never ask for or repeat secrets such as API keys or passwords.
- Use the conversation so far: refer back to what the user said earlier when it is relevant."""

SUMMARY_PROMPT = """You maintain a running summary of a conversation between a user and a programming mentor.
Merge the PREVIOUS SUMMARY with the NEW MESSAGES into one updated summary.
Keep: the user's name/goals/skill level, languages and tools in use, decisions made, open problems,
and any facts the user stated. Drop pleasantries. Max 150 words. Output only the summary."""
