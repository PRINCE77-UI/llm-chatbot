"""Terminal interface: python cli.py   (commands: /reset, /quit, /debug)"""
from app import llm
from app.conversation import Conversation

conv = Conversation()
print("Byte - programming mentor. Type /reset to start over, /debug to inspect memory, /quit to exit.\n")

while True:
    try:
        text = input("you > ").strip()
    except (EOFError, KeyboardInterrupt):
        break
    if not text:
        continue
    if text == "/quit":
        break
    if text == "/reset":
        conv = Conversation()
        print("(conversation cleared)\n")
        continue
    if text == "/debug":
        print(f"[messages in window: {len(conv.messages)}]\n[summary: {conv.summary or 'none yet'}]\n")
        continue
    try:
        reply, trimmed = conv.send(text, llm.generate, llm.summarize)
    except llm.LLMError as e:
        print(f"! {e.user_message}\n")
        continue
    if trimmed:
        print("(older messages were summarised to save context)")
    print(f"byte > {reply}\n")
