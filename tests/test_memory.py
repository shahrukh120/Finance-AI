"""
Tests for the Memory System (Short-term and Long-term memory).
Run with: python -m pytest tests/ -v
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from memory.memory_system import ShortTermMemory, LongTermMemory, MemoryManager


class TestShortTermMemory:
    def test_add_conversation_entry(self, test_user):
        stm = ShortTermMemory(user_id=test_user.id)
        stm.add_conversation_entry("user", "Hello")
        assert len(stm.conversation_context) == 1
        assert stm.conversation_context[0]["role"] == "user"
        assert stm.conversation_context[0]["message"] == "Hello"

    def test_conversation_limit(self, test_user):
        stm = ShortTermMemory(user_id=test_user.id)
        for i in range(25):
            stm.add_conversation_entry("user", f"Message {i}")
        assert len(stm.conversation_context) == 20

    def test_add_alert(self, test_user):
        stm = ShortTermMemory(user_id=test_user.id)
        stm.add_alert("food", "Over budget!", "critical")
        assert len(stm.active_alerts) == 1
        assert stm.active_alerts[0]["severity"] == "critical"

    def test_clear_alerts(self, test_user):
        stm = ShortTermMemory(user_id=test_user.id)
        stm.add_alert("food", "Alert 1")
        stm.add_alert("transport", "Alert 2")
        stm.clear_alerts()
        assert len(stm.active_alerts) == 0

    def test_store_and_get_calculation(self, test_user):
        stm = ShortTermMemory(user_id=test_user.id)
        stm.store_calculation("total_food", 305.50)
        assert stm.get_calculation("total_food") == 305.50
        assert stm.get_calculation("nonexistent") is None

    def test_context_summary(self, test_user):
        stm = ShortTermMemory(user_id=test_user.id)
        stm.add_alert("food", "Test alert")
        stm.store_calculation("key1", 100)
        summary = stm.get_context_summary()
        assert "active_alerts" in summary
        assert len(summary["active_alerts"]) == 1
        assert "key1" in summary["stored_calculations"]


class TestLongTermMemory:
    def test_load_user_profile(self, test_user):
        ltm = LongTermMemory(user_id=test_user.id)
        assert ltm.user_profile.get("monthly_income", 0) > 0
        assert len(ltm.get_budget_limits()) == 5

    def test_load_spending_history(self, test_user):
        ltm = LongTermMemory(user_id=test_user.id)
        assert len(ltm.spending_history) >= 25

    def test_get_spending_by_category(self, test_user):
        ltm = LongTermMemory(user_id=test_user.id)
        food = ltm.get_spending_by_category("food", "2026-03-01", "2026-03-31")
        assert len(food) > 0
        assert all(e["category"] == "food" for e in food)

    def test_add_transaction(self, test_user):
        ltm = LongTermMemory(user_id=test_user.id)
        initial_count = len(ltm.spending_history)
        ltm.add_transaction({
            "category": "food",
            "amount": 15.00,
            "description": "Test transaction",
            "date": "2026-03-30",
        })
        assert len(ltm.spending_history) == initial_count + 1

    def test_update_goal(self, test_user):
        ltm = LongTermMemory(user_id=test_user.id)
        ltm.update_goal("Emergency Fund", 5000.00)
        goal = next(g for g in ltm.financial_goals if g["name"] == "Emergency Fund")
        assert goal["current_amount"] == 5000.00

    def test_save(self, test_user):
        ltm = LongTermMemory(user_id=test_user.id)
        ltm.save()  # Should not raise (just commits DB)


class TestMemoryManager:
    def test_initialization(self, test_user):
        mm = MemoryManager(user_id=test_user.id)
        assert mm.short_term is not None
        assert mm.long_term is not None

    def test_add_expense(self, test_user):
        mm = MemoryManager(user_id=test_user.id)
        initial = len(mm.long_term.spending_history)
        mm.add_expense("food", 25.00, "Test expense")
        assert len(mm.long_term.spending_history) == initial + 1

    def test_get_full_context(self, test_user):
        mm = MemoryManager(user_id=test_user.id)
        ctx = mm.get_full_context()
        assert "budget_limits" in ctx
        assert "monthly_income" in ctx
        assert "financial_goals" in ctx
        assert ctx["monthly_income"] > 0

    def test_log_interaction(self, test_user):
        mm = MemoryManager(user_id=test_user.id)
        mm.log_interaction("test_agent", "test_action", {"key": "value"})
        assert len(mm.short_term.conversation_context) >= 1

    def test_save_all(self, test_user):
        mm = MemoryManager(user_id=test_user.id)
        mm.save_all()  # Should not raise
