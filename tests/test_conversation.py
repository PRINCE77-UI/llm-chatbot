import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.conversation import Conversation  # noqa: E402


def fake_generate(system, messages):
    return f"echo:{messages[-1]['content']}"


def fake_summarize(prev, old):
    return (prev + " | " if prev else "") + f"{len(old)} msgs: " + old[0]["content"]


class ConversationTests(unittest.TestCase):
    def test_history_is_sent_to_model(self):
        seen = {}

        def gen(system, messages):
            seen["n"] = len(messages)
            return "ok"

        c = Conversation(max_messages=12, keep_recent=6)
        for i in range(3):
            c.send(f"m{i}", gen)
        self.assertEqual(seen["n"], 5)  # 2 prior turns (4 msgs) + new user msg

    def test_summarises_when_too_long(self):
        c = Conversation(max_messages=6, keep_recent=2)
        for i in range(8):
            c.send(f"m{i}", fake_generate, fake_summarize)
        self.assertLessEqual(len(c.messages), 6 + 2)
        self.assertIn("m0", c.summary)
        self.assertIn("Summary of the earlier", c.system_prompt())
        self.assertEqual(c.messages[0]["role"], "user")

    def test_summariser_failure_falls_back_to_truncation(self):
        def boom(prev, old):
            raise RuntimeError("api down")

        c = Conversation(max_messages=4, keep_recent=2)
        for i in range(6):
            c.send(f"m{i}", fake_generate, boom)
        self.assertLessEqual(len(c.messages), 4 + 2)
        self.assertEqual(c.summary, "")

    def test_failed_call_does_not_corrupt_history(self):
        c = Conversation()
        c.send("hello", fake_generate)

        def fail(system, messages):
            raise TimeoutError()

        with self.assertRaises(TimeoutError):
            c.send("this fails", fail)
        self.assertEqual([m["role"] for m in c.messages], ["user", "model"])


if __name__ == "__main__":
    unittest.main()
