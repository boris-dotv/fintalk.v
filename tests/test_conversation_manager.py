"""Unit tests for enhanced_core.conversation_manager pure logic.

These tests exercise only stdlib-backed behaviour: history bookkeeping,
context updates, entity de-duplication and reset semantics. No network,
API keys or heavy dependencies are required.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enhanced_core.conversation_manager import ConversationManager, ConversationTurn


class TestConversationTurn(unittest.TestCase):
    def test_defaults(self):
        turn = ConversationTurn(user="hello")
        self.assertEqual(turn.user, "hello")
        self.assertEqual(turn.assistant, "")
        self.assertEqual(turn.query_type, "")
        self.assertEqual(turn.metadata, {})
        self.assertIsInstance(turn.timestamp, float)

    def test_metadata_is_not_shared_between_instances(self):
        a = ConversationTurn(user="a")
        b = ConversationTurn(user="b")
        a.metadata["k"] = 1
        self.assertEqual(b.metadata, {})


class TestConversationManagerHistory(unittest.TestCase):
    def setUp(self):
        self.cm = ConversationManager(max_history=3)

    def test_add_turn_appends_history(self):
        self.cm.add_turn("q1", "a1", query_type="sql")
        self.cm.add_turn("q2", "a2")
        self.assertEqual(len(self.cm.history), 2)
        self.assertEqual(self.cm.history[0].user, "q1")
        self.assertEqual(self.cm.history[0].assistant, "a1")
        self.assertEqual(self.cm.history[0].query_type, "sql")

    def test_max_history_trims_oldest(self):
        for i in range(5):
            self.cm.add_turn(f"q{i}", f"a{i}")
        self.assertEqual(len(self.cm.history), 3)
        self.assertEqual([t.user for t in self.cm.history], ["q2", "q3", "q4"])

    def test_get_history_text_formats_recent_turns(self):
        self.cm.add_turn("q1", "a1")
        self.cm.add_turn("q2", "a2")
        text = self.cm.get_history_text(n_turns=1)
        self.assertEqual(text, "User: q2\nAssistant: a2")

    def test_get_history_text_skips_empty_assistant(self):
        self.cm.add_turn("q1", "")
        self.assertEqual(self.cm.get_history_text(), "User: q1")

    def test_get_history_text_empty_history(self):
        self.assertEqual(self.cm.get_history_text(), "")

    def test_get_last_query_and_assistant(self):
        self.assertIsNone(self.cm.get_last_query())
        self.assertIsNone(self.cm.get_last_assistant())
        self.cm.add_turn("q1", "a1")
        self.assertEqual(self.cm.get_last_query(), "q1")
        self.assertEqual(self.cm.get_last_assistant(), "a1")


class TestConversationManagerContext(unittest.TestCase):
    def setUp(self):
        self.cm = ConversationManager()

    def test_company_detection_is_case_insensitive(self):
        self.cm.add_turn("tell me about za bank", "ok")
        self.assertEqual(self.cm.context["last_company"], "ZA Bank")
        self.assertIn("ZA Bank", self.cm.context["entities"])

    def test_entity_deduplication(self):
        self.cm.add_turn("ZA Bank", "ok")
        self.cm.add_turn("ZA Bank again", "ok")
        self.assertEqual(self.cm.context["entities"].count("ZA Bank"), 1)

    def test_unknown_company_leaves_last_company_none(self):
        self.cm.add_turn("what is the weather", "ok")
        self.assertIsNone(self.cm.context["last_company"])
        self.assertEqual(self.cm.context["entities"], [])

    def test_last_query_fields_always_updated(self):
        self.cm.add_turn("first", "a")
        self.cm.add_turn("second", "b")
        self.assertEqual(self.cm.context["last_query"], "second")
        self.assertEqual(self.cm.context["last_user_query"], "second")
        self.assertIsNotNone(self.cm.context["last_query_time"])

    def test_last_query_type_taken_from_latest_turn(self):
        self.cm.add_turn("q1", "a1", query_type="sql")
        self.assertEqual(self.cm.context["last_query_type"], "sql")
        # A later turn without a query_type must not clear the previous value.
        self.cm.add_turn("q2", "a2")
        self.assertEqual(self.cm.context["last_query_type"], "sql")

    def test_context_summary_without_context(self):
        self.assertEqual(self.cm.get_context_summary(), "No context")

    def test_context_summary_with_company_and_entities(self):
        self.cm.add_turn("ZA Bank and Mox Bank", "ok")
        summary = self.cm.get_context_summary()
        self.assertIn("Last company: ZA Bank", summary)
        self.assertIn("Entities: ZA Bank", summary)


class TestConversationManagerReset(unittest.TestCase):
    def test_clear_resets_history_context_and_slots(self):
        cm = ConversationManager()
        cm.add_turn("ZA Bank", "ok")
        cm.slots["company"] = "ZA Bank"
        result = cm.clear()
        self.assertIs(result, cm)
        self.assertEqual(len(cm.history), 0)
        self.assertIsNone(cm.context["last_company"])
        self.assertEqual(cm.context["entities"], [])
        self.assertEqual(cm.slots, {})

    def test_get_stats(self):
        cm = ConversationManager()
        cm.add_turn("ZA Bank", "ok")
        cm.slots["a"] = 1
        stats = cm.get_stats()
        self.assertEqual(stats["total_turns"], 1)
        self.assertEqual(stats["last_company"], "ZA Bank")
        self.assertEqual(stats["entities_count"], 1)
        self.assertEqual(stats["slots_count"], 1)


if __name__ == "__main__":
    unittest.main()
