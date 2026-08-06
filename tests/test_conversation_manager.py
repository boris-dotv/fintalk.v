"""Unit tests for enhanced_core.conversation_manager.ConversationManager."""

from enhanced_core.conversation_manager import (
    ConversationManager,
    ConversationTurn,
)


class TestConversationTurn:
    def test_defaults(self):
        turn = ConversationTurn(user="hi")
        assert turn.user == "hi"
        assert turn.assistant == ""
        assert turn.query_type == ""
        assert turn.metadata == {}
        assert isinstance(turn.timestamp, float)


class TestAddTurnAndHistory:
    def test_add_turn_appends_to_history(self):
        cm = ConversationManager()
        cm.add_turn("What is ZA Bank's size?", "501-1000 employees", "task")
        assert len(cm.history) == 1
        turn = cm.history[-1]
        assert turn.user == "What is ZA Bank's size?"
        assert turn.assistant == "501-1000 employees"
        assert turn.query_type == "task"

    def test_history_respects_max_history(self):
        cm = ConversationManager(max_history=3)
        for i in range(5):
            cm.add_turn(f"q{i}", f"a{i}")
        assert len(cm.history) == 3
        # Oldest turns dropped; only the last three remain.
        assert [t.user for t in cm.history] == ["q2", "q3", "q4"]

    def test_metadata_defaults_to_empty_dict(self):
        cm = ConversationManager()
        cm.add_turn("q", "a")
        assert cm.history[-1].metadata == {}

    def test_metadata_is_preserved(self):
        cm = ConversationManager()
        cm.add_turn("q", "a", metadata={"foo": "bar"})
        assert cm.history[-1].metadata == {"foo": "bar"}


class TestContextTracking:
    def test_extracts_known_company(self):
        cm = ConversationManager()
        cm.add_turn("Tell me about WeLab Bank", "ok")
        assert cm.context["last_company"] == "WeLab Bank"
        assert "WeLab Bank" in cm.context["entities"]

    def test_case_insensitive_company_match(self):
        cm = ConversationManager()
        cm.add_turn("what about za bank employees", "ok")
        assert cm.context["last_company"] == "ZA Bank"

    def test_entities_are_deduplicated(self):
        cm = ConversationManager()
        cm.add_turn("ZA Bank info", "ok")
        cm.add_turn("more on ZA Bank", "ok")
        assert cm.context["entities"].count("ZA Bank") == 1

    def test_last_company_updates_to_most_recent(self):
        cm = ConversationManager()
        cm.add_turn("ZA Bank info", "ok")
        cm.add_turn("Mox Bank info", "ok")
        assert cm.context["last_company"] == "Mox Bank"
        assert set(cm.context["entities"]) == {"ZA Bank", "Mox Bank"}


class TestGetHistoryText:
    def test_formats_recent_turns(self):
        cm = ConversationManager()
        cm.add_turn("q1", "a1")
        cm.add_turn("q2", "a2")
        text = cm.get_history_text(n_turns=2)
        assert text == "User: q1\nAssistant: a1\nUser: q2\nAssistant: a2"

    def test_limits_to_n_turns(self):
        cm = ConversationManager()
        for i in range(4):
            cm.add_turn(f"q{i}", f"a{i}")
        text = cm.get_history_text(n_turns=1)
        assert "q3" in text
        assert "q0" not in text

    def test_omits_empty_assistant_answer(self):
        cm = ConversationManager()
        cm.add_turn("q1", "")
        text = cm.get_history_text()
        assert text == "User: q1"

    def test_empty_history_returns_empty_string(self):
        cm = ConversationManager()
        assert cm.get_history_text() == ""


class TestContextSummaryAndLastQuery:
    def test_context_summary_with_data(self):
        cm = ConversationManager()
        cm.add_turn("ZA Bank details", "ok")
        summary = cm.get_context_summary()
        assert "Last company: ZA Bank" in summary
        assert "Entities: ZA Bank" in summary

    def test_context_summary_no_context(self):
        cm = ConversationManager()
        assert cm.get_context_summary() == "No context"

    def test_get_last_query(self):
        cm = ConversationManager()
        assert cm.get_last_query() is None
        cm.add_turn("first", "a")
        cm.add_turn("second", "a")
        assert cm.get_last_query() == "second"


class TestClearAndStats:
    def test_clear_resets_state(self):
        cm = ConversationManager()
        cm.add_turn("ZA Bank details", "ok")
        cm.slots["x"] = 1
        cm.clear()
        assert len(cm.history) == 0
        assert cm.context["last_company"] is None
        assert cm.context["entities"] == []
        assert cm.slots == {}

    def test_get_stats(self):
        cm = ConversationManager()
        cm.add_turn("ZA Bank details", "ok")
        cm.add_turn("Mox Bank details", "ok")
        cm.slots["a"] = 1
        stats = cm.get_stats()
        assert stats["total_turns"] == 2
        assert stats["last_company"] == "Mox Bank"
        assert stats["entities_count"] == 2
        assert stats["slots_count"] == 1
