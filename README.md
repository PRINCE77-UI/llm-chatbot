# Byte: a multi-turn LLM chatbot with context window management

Byte is a programming-mentor chatbot built on the **Google Gemini API**. It remembers the conversation, keeps its context window under control with a **sliding window plus a running summary**, and handles API failures without breaking the UI. It ships with a FastAPI backend, a web interface, and a terminal interface.

<!-- Add a screenshot after your first run: save it as docs/screenshot.png and uncomment the next line.
![Byte chat interface](docs/screenshot.png)
-->

## Features

- **Real LLM backend**: `POST /chat` forwards messages to Gemini and returns the reply.
- **Per-conversation memory**: every conversation has its own `conversation_id` and message history, so the model can refer back to what was said earlier.
- **Context window management**: recent messages are kept verbatim; older ones are summarised by the model into a running summary that is added to the system prompt. If summarising fails, it falls back to plain truncation.
- **A defined persona**: the system prompt makes the bot "Byte", a friendly programming mentor with clear style and boundaries.
- **Error handling**: rate limits, bad keys, timeouts, network failures, and empty replies all produce a clear message. Temporary server errors (429/5xx) are retried automatically. The UI shows a Retry button.
- **Secrets stay out of git**: the API key lives in `.env`, which is git-ignored.
- **Two interfaces**: a web UI (code blocks with copy button, dark mode, memory indicator) and a CLI.
- **Offline tests** for the history and context logic (no API key needed).

## Tech stack

Python 3.10+, FastAPI, Uvicorn, `google-genai` SDK, plain HTML/CSS/JavaScript (no build step).

## Quick start

**1. Clone and enter the project**

```bash
git clone https://github.com/<your-username>/llm-chatbot.git
cd llm-chatbot
```

**2. Create a virtual environment and install dependencies**

Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS / Linux:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**3. Add your API key**

Get a free key at <https://aistudio.google.com/apikey>, then:

```bash
cp .env.example .env        # Windows: copy .env.example .env
```

Open `.env` and set:

```
GEMINI_API_KEY=your-real-key
```

**4. Run it**

Web UI:
```bash
uvicorn app.main:app --reload
```
Then open <http://127.0.0.1:8000>.

Terminal version:
```bash
python cli.py
```
CLI commands: `/reset` (new conversation), `/debug` (show window size and summary), `/quit`.

## Configuration

All settings are environment variables (set them in `.env`).

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | none (required) | Your Gemini API key |
| `GEMINI_MODEL` | see `app/config.py` | Model name. Google retires models over time, so if you get a 404 or 503 pick another one (see below) |
| `MAX_MESSAGES` | `12` | When history grows past this, older messages are summarised |
| `KEEP_RECENT` | `6` | Number of recent messages always kept verbatim |
| `REQUEST_TIMEOUT_S` | `30` | Per-request timeout in seconds |

**Choosing a model.** List the models your key can use:

```bash
python -c "from google import genai; import os; from dotenv import load_dotenv; load_dotenv(); c=genai.Client(api_key=os.getenv('GEMINI_API_KEY')); [print(m.name) for m in c.models.list()]"
```

Pick a text model (a `flash` or `flash-lite` one is a good choice), drop the `models/` prefix, and put it in `.env` as `GEMINI_MODEL=...`.

## How context management works

LLMs only know what you send them on each request, and every model has a finite context window. Byte handles this in `app/conversation.py`:

1. Every request sends the system prompt plus the stored message history.
2. When the history exceeds `MAX_MESSAGES`, the messages older than the last `KEEP_RECENT` are sent to the model with a summarisation prompt, together with the previous summary.
3. The result becomes the new **running summary**. It is appended to the system prompt on every later request, and the old messages are dropped.
4. If the summarisation call fails, the old messages are simply truncated, so the chat never stops working and the context never grows without bound.
5. If a chat request fails, the unanswered user message is removed, so the history never contains a dangling turn.

To watch it happen, set `MAX_MESSAGES=6` and `KEEP_RECENT=2` in `.env`, run `python cli.py`, chat for a few turns, and type `/debug`.

## Error handling

| Situation | What the user sees |
|---|---|
| Missing API key | "The server has no API key configured..." |
| Rate limit (429) | "The model is rate-limited right now..." (retried automatically first) |
| Server overloaded (5xx) | Retried up to 3 times, then "The model service is busy or had a problem..." |
| Bad key (401/403) | "The API key was rejected..." |
| Wrong model name (400/404) | "The request was rejected by the model API. Check GEMINI_MODEL..." |
| Timeout | "The model took too long to respond..." |
| Network failure | "Could not reach the model service..." |
| Empty or blocked reply | "The model returned an empty reply. Try rephrasing..." |
| Backend not running | "Could not reach the server..." with a Retry button |

## Project structure

```
llm-chatbot/
├── app/
│   ├── config.py          # settings, system prompt, summary prompt
│   ├── llm.py             # all Gemini-specific code, retries, error mapping
│   ├── conversation.py    # history + context window management
│   └── main.py            # FastAPI app: /chat, /reset, serves the UI
├── static/index.html      # web interface
├── tests/
│   └── test_conversation.py
├── cli.py                 # terminal interface
├── requirements.txt
├── .env.example           # template; copy to .env
└── .gitignore             # keeps .env and .venv out of git
```

## API

`POST /chat`

```json
{ "message": "What is a list comprehension?", "conversation_id": null }
```

Response:

```json
{ "conversation_id": "9f2c...", "reply": "...", "history_trimmed": false }
```

Send the returned `conversation_id` with every later message to continue the same conversation. `POST /reset` with `{ "conversation_id": "..." }` clears it.

## Tests

```bash
python -m unittest discover tests
```

These run offline with fake model functions and check that history is passed on, that older messages are summarised, that summarisation failure falls back to truncation, and that a failed call does not corrupt history.

## Try the memory yourself

1. "Hi, I'm prince and I'm learning Python."
2. "What's a list comprehension?"
3. "Show me one that squares numbers."
4. "Now do the same with a for loop."
5. "What was my name and what language am I learning?" The bot should answer **Sam** and **Python**.

## Switching to OpenAI

All provider-specific code is in `app/llm.py` (the `generate` and `summarize` functions). To use OpenAI, reimplement those two functions with the `openai` SDK and map the role `"model"` to `"assistant"`. Nothing else needs to change.

## Security notes

- `.env` is listed in `.gitignore`; only `.env.example` (with a placeholder) is committed.
- Before your first `git add`, run `git status` and confirm `.env` is not listed.
- If a key is ever committed by mistake, revoke it in Google AI Studio and create a new one. Deleting the file in a later commit is not enough, because git history keeps it.

## Limitations and ideas for next steps

- Conversations are stored in memory, so they reset when the server restarts. A database or Redis would fix that.
- Replies arrive all at once; streaming responses would feel faster.
- Context size is counted in messages, not tokens. Counting tokens would use the window more precisely.
- No user authentication or rate limiting on the endpoint.
