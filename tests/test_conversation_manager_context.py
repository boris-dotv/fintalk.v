#!/usr/bin/env python3
"""Unit tests for ConversationManager context and history handling.

The module is pure stdlib (logging, time, collections, dataclasses),
so it can be exercised without network or heavy dependencies.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enhanced_core.conversation_manager import ConversationManager  # noqa: E402


class TestAddTurnAndHistory(unittest.TestCase):
    def test_add_turn_appends_to_history(self):
        cm = ConversationManager()
        cm.add_turn("Tell me about ZA Bank", "ZA Bank is a virtual bank")
        self.assertEqual(len(cm.history), 1)
        self.assertEqual(cm.history[-1].user, "Tell me about ZA Bank")
        self.assertEqual(cm.history[-1].assistant, "ZA Bank is a virtual bank")

    def test_history_is_bounded_by_max_history(self):
        cm = ConversationManager(max_history=2)
        for i in range(5):
            cm.add_turn(f"q{i}", f"a{i}")
        self.assertEqual(len(cm.history), 2)
        self.assertEqual(cm.history[0].user, "q3")
        self.assertEqual(cm.history[-1].user, "q4")

    def test_query_type_recorded_on_turn_and_context(self):
        cm = ConversationManager()
        cm.add_turn("q", "a", query_type="comparison")
        self.assertEqual(cm.history[-1].query_type, "comparison")
        self.assertEqual(cm.context["last_query_type"], "comparison")

    def test_metadata_defaults_to_empty_dict(self):
        cm = ConversationManager()
        cm.add_turn("q", "a")
        self.assertEqual(cm.history[-1].metadata, {})


class TestContextUpdates(unittest.TestCase):
    def test_company_detection_is_case_insensitive(self):
        cm = ConversationManager()
        cm.add_turn("tell me about za bank", "ok")
        self.assertEqual(cm.context["last_company"], "ZA Bank")
        self.assertIn("ZA Bank", cm.context["entities"])

    def test_entities_are_not_duplicated(self):
        cm = ConversationManager()
        cm.add_turn("ZA Bank", "ok")
        cm.add_turn("ZA Bank again", "ok")
        self.assertEqual(cm.context["entities"].count("ZA Bank"), 1)

    def test_last_query_fields_always_updated(self):
        cm = ConversationManager()
        cm.add_turn("first query", "ok")
        cm.add_turn("second query", "ok")
        self.assertEqual(cm.context["last_query"], "second query")
        self.assertEqual(cm.context["last_user_query"], "second query")
        self.assertIsNotNone(cm.context["last_query_time"])

    def test_unknown_company_leaves_last_company_none(self):
        cm = ConversationManager()
        cm.add_turn("Tell me about Some Other Corp", "ok")
        self.assertIsNone(cm.context["last_company"])


class TestHistoryTextAndAccessors(unittest.TestCase):
    def test_history_text_includes_user_and_assistant(self):
        cm = ConversationManager()
        cm.add_turn("hello", "hi there")
        text = cm.get_history_text()
        self.assertIn("User: hello", text)
        self.assertIn("Assistant: hi there", text)

    def test_history_text_omits_empty_assistant(self):
        cm = ConversationManager()
        cm.add_turn("hello", "")
        text = cm.get_history_text()
        self.assertIn("User: hello", text)
        self.assertNotIn("Assistant:", text)

    def test_history_text_limits_turns(self):
        cm = ConversationManager()
        for i in range(4):
            cm.add_turn(f"q{i}", f"a{i}")
        text = cm.get_history_text(n_turns=1)
        self.assertIn("q3", text)
        self.assertNotIn("q2", text)

    def test_last_query_and_assistant_accessors(self):
        cm = ConversationManager()
        self.assertIsNone(cm.get_last_query())
        self.assertIsNone(cm.get_last_assistant())
        cm.add_turn("q", "a")
        self.assertEqual(cm.get_last_query(), "q")
        self.assertEqual(cm.get_last_assistant(), "a")

    def test_context_summary_without_context(self):
        cm = ConversationManager()
        self.assertEqual(cm.get_context_summary(), "No context")

    def test_context_summary_with_company(self):
        cm = ConversationManager()
        cm.add_turn("ZA Bank", "ok")
        summary = cm.get_context_summary()
        self.assertIn("ZA Bank", summary)


class TestClearAndStats(unittest.TestCase):
    def test_clear_resets_history_context_and_slots(self):
        cm = ConversationManager()
        cm.add_turn("ZA Bank", "ok")
        cm.slots["x"] = 1
        returned = cm.clear()
        self.assertIs(returned, cm)
        self.assertEqual(len(cm.history), 0)
        self.assertIsNone(cm.context["last_company"])
        self.assertEqual(cm.context["entities"], [])
        self.assertEqual(cm.slots, {})

    def test_stats_reports_counts(self):
        cm = ConversationManager()
        cm.add_turn("ZA Bank", "ok")
        cm.slots["x"] = 1
        stats = cm.get_stats()
        self.assertEqual(stats["total_turns"], 1)
        self.assertEqual(stats["last_company"], "ZA Bank")
        self.assertEqual(stats["entities_count"], 1)
        self.assertEqual(stats["slots_count"], 1)


if __name__ == "__main__":
    unittest.main()
