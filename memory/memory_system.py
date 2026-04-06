"""
Memory System for Personal Finance Manager Agent.

Implements Short-term Memory (recent context) and Long-term Memory (persistent history).
Uses the database when a user_id is provided (web mode), or JSON files as fallback (CLI mode).
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
MEMORY_DIR = os.path.join(os.path.dirname(__file__), "storage")


class ShortTermMemory:
    """
    Short-term memory holds transient, session-relevant data:
    - Current conversation context
    - Recent transactions (last 7 days)
    - Active budget alerts
    - Temporary calculation results
    """

    def __init__(self, user_id=None):
        self.user_id = user_id
        self.conversation_context: list[dict] = []
        self.recent_transactions: list[dict] = []
        self.active_alerts: list[dict] = []
        self.calculation_results: dict[str, Any] = {}
        self._load_recent_transactions()

    def _load_recent_transactions(self):
        """Load transactions from the last 7 days."""
        if self.user_id is not None:
            from models import Expense
            cutoff = (datetime.now() - timedelta(days=7)).date()
            rows = Expense.query.filter(
                Expense.user_id == self.user_id,
                Expense.date >= cutoff,
            ).all()
            self.recent_transactions = [
                {
                    "id": r.id,
                    "date": r.date.strftime("%Y-%m-%d"),
                    "category": r.category,
                    "amount": r.amount,
                    "description": r.description or "",
                }
                for r in rows
            ]
            return

        # Fallback: JSON file (CLI mode)
        expenses_path = os.path.join(DATA_DIR, "sample_expenses.json")
        if not os.path.exists(expenses_path):
            return
        with open(expenses_path, "r") as f:
            all_expenses = json.load(f)
        cutoff = datetime.now() - timedelta(days=7)
        self.recent_transactions = [
            exp for exp in all_expenses
            if datetime.strptime(exp["date"], "%Y-%m-%d") >= cutoff
        ]

    def add_conversation_entry(self, role: str, message: str):
        """Add an entry to the conversation context."""
        self.conversation_context.append({
            "role": role,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        })
        if len(self.conversation_context) > 20:
            self.conversation_context = self.conversation_context[-20:]

    def add_alert(self, category: str, message: str, severity: str = "warning"):
        """Add a budget alert."""
        self.active_alerts.append({
            "category": category,
            "message": message,
            "severity": severity,
            "timestamp": datetime.now().isoformat(),
        })

    def clear_alerts(self):
        """Clear all active alerts."""
        self.active_alerts = []

    def store_calculation(self, key: str, value: Any):
        """Store a temporary calculation result."""
        self.calculation_results[key] = {
            "value": value,
            "timestamp": datetime.now().isoformat(),
        }

    def get_calculation(self, key: str) -> Any:
        """Retrieve a stored calculation result."""
        entry = self.calculation_results.get(key)
        return entry["value"] if entry else None

    def get_context_summary(self) -> dict:
        """Return a summary of current short-term memory state."""
        return {
            "conversation_entries": len(self.conversation_context),
            "recent_transactions_count": len(self.recent_transactions),
            "active_alerts": self.active_alerts,
            "stored_calculations": list(self.calculation_results.keys()),
        }


class LongTermMemory:
    """
    Long-term memory holds persistent data across sessions:
    - User's monthly income and budget limits
    - Complete spending history
    - Financial goals with target dates
    - User preferences
    """

    def __init__(self, user_id=None):
        self.user_id = user_id
        os.makedirs(MEMORY_DIR, exist_ok=True)
        self.user_profile: dict = {}
        self.spending_history: list[dict] = []
        self.financial_goals: list[dict] = []
        self.preferences: dict = {}
        self.load()

    def load(self):
        """Load all long-term memory from DB or files."""
        if self.user_id is not None:
            self._load_from_db()
            return
        self._load_from_files()

    def _load_from_db(self):
        """Load long-term memory from the database."""
        from models import Budget, Expense, Goal, User, db

        user = db.session.get(User, self.user_id)
        if not user:
            return

        budgets = {b.category: b.limit_amount for b in Budget.query.filter_by(user_id=self.user_id)}
        goals = [
            {
                "name": g.name,
                "target_amount": g.target_amount,
                "current_amount": g.current_amount,
                "target_date": g.target_date.strftime("%Y-%m-%d") if g.target_date else None,
            }
            for g in Goal.query.filter_by(user_id=self.user_id)
        ]

        self.user_profile = {
            "name": user.name,
            "monthly_income": user.monthly_income,
            "currency": user.currency,
            "budget_limits": budgets,
            "financial_goals": goals,
            "preferences": {
                "alert_threshold_percentage": user.alert_threshold_percentage,
                "preferred_savings_rate": user.preferred_savings_rate,
                "report_frequency": user.report_frequency,
            },
        }
        self.financial_goals = goals
        self.preferences = self.user_profile["preferences"]

        rows = Expense.query.filter_by(user_id=self.user_id).all()
        self.spending_history = [
            {
                "id": r.id,
                "date": r.date.strftime("%Y-%m-%d"),
                "category": r.category,
                "amount": r.amount,
                "description": r.description or "",
            }
            for r in rows
        ]

    def _load_from_files(self):
        """Load long-term memory from JSON files (CLI fallback)."""
        profile_path = os.path.join(DATA_DIR, "user_profile.json")
        if os.path.exists(profile_path):
            with open(profile_path, "r") as f:
                profile = json.load(f)
            self.user_profile = profile
            self.financial_goals = profile.get("financial_goals", [])
            self.preferences = profile.get("preferences", {})

        expenses_path = os.path.join(DATA_DIR, "sample_expenses.json")
        if os.path.exists(expenses_path):
            with open(expenses_path, "r") as f:
                self.spending_history = json.load(f)

        persisted_path = os.path.join(MEMORY_DIR, "long_term_memory.json")
        if os.path.exists(persisted_path):
            with open(persisted_path, "r") as f:
                persisted = json.load(f)
            if persisted.get("additional_transactions"):
                self.spending_history.extend(persisted["additional_transactions"])
            if persisted.get("financial_goals"):
                self.financial_goals = persisted["financial_goals"]
            if persisted.get("preferences"):
                self.preferences.update(persisted["preferences"])

    def save(self):
        """Persist long-term memory."""
        if self.user_id is not None:
            from models import db
            db.session.commit()
            return

        # Fallback: save to JSON file (CLI mode)
        original_ids = set()
        expenses_path = os.path.join(DATA_DIR, "sample_expenses.json")
        if os.path.exists(expenses_path):
            with open(expenses_path, "r") as f:
                for exp in json.load(f):
                    original_ids.add(exp["id"])

        additional = [t for t in self.spending_history if t.get("id") not in original_ids]

        persisted = {
            "additional_transactions": additional,
            "financial_goals": self.financial_goals,
            "preferences": self.preferences,
            "last_saved": datetime.now().isoformat(),
        }
        persisted_path = os.path.join(MEMORY_DIR, "long_term_memory.json")
        with open(persisted_path, "w") as f:
            json.dump(persisted, f, indent=2)

    def add_transaction(self, transaction: dict):
        """Add a new transaction to spending history."""
        if self.user_id is not None:
            from models import Expense, db
            exp = Expense(
                user_id=self.user_id,
                date=datetime.strptime(transaction.get("date", datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d").date(),
                category=transaction["category"],
                amount=transaction["amount"],
                description=transaction.get("description", ""),
            )
            db.session.add(exp)
            db.session.commit()
            transaction["id"] = exp.id
            self.spending_history.append(transaction)
            return

        # Fallback: in-memory only (CLI mode)
        if "id" not in transaction:
            max_id = max((t.get("id", 0) for t in self.spending_history), default=0)
            transaction["id"] = max_id + 1
        if "date" not in transaction:
            transaction["date"] = datetime.now().strftime("%Y-%m-%d")
        self.spending_history.append(transaction)

    def get_budget_limits(self) -> dict:
        """Return the user's budget limits per category."""
        return self.user_profile.get("budget_limits", {})

    def get_monthly_income(self) -> float:
        """Return the user's monthly income."""
        return self.user_profile.get("monthly_income", 0.0)

    def get_spending_by_category(self, category: str, start_date: str = None, end_date: str = None) -> list[dict]:
        """Get all transactions for a category within an optional date range."""
        result = [t for t in self.spending_history if t["category"] == category]
        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            result = [t for t in result if datetime.strptime(t["date"], "%Y-%m-%d") >= start]
        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d")
            result = [t for t in result if datetime.strptime(t["date"], "%Y-%m-%d") <= end]
        return result

    def get_all_spending(self, start_date: str = None, end_date: str = None) -> list[dict]:
        """Get all transactions within an optional date range."""
        result = self.spending_history
        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            result = [t for t in result if datetime.strptime(t["date"], "%Y-%m-%d") >= start]
        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d")
            result = [t for t in result if datetime.strptime(t["date"], "%Y-%m-%d") <= end]
        return result

    def update_goal(self, goal_name: str, current_amount: float):
        """Update progress on a financial goal."""
        if self.user_id is not None:
            from models import Goal, db
            goal = Goal.query.filter_by(user_id=self.user_id, name=goal_name).first()
            if goal:
                goal.current_amount = current_amount
                db.session.commit()
        for goal in self.financial_goals:
            if goal["name"] == goal_name:
                goal["current_amount"] = current_amount
                break


class MemoryManager:
    """
    Central memory manager that coordinates short-term and long-term memory.
    Provides a unified interface for agents to read/write memory.
    """

    def __init__(self, user_id=None):
        self.user_id = user_id
        self.short_term = ShortTermMemory(user_id=user_id)
        self.long_term = LongTermMemory(user_id=user_id)

    def log_interaction(self, agent_name: str, action: str, data: Any = None):
        """Log an agent interaction to short-term memory."""
        self.short_term.add_conversation_entry(
            role=agent_name,
            message=f"{action}: {json.dumps(data) if data else 'N/A'}",
        )

    def add_expense(self, category: str, amount: float, description: str):
        """Add a new expense and update both memory systems."""
        transaction = {
            "category": category,
            "amount": amount,
            "description": description,
            "date": datetime.now().strftime("%Y-%m-%d"),
        }
        self.long_term.add_transaction(transaction)
        self.short_term.recent_transactions.append(transaction)
        self.log_interaction("system", "expense_added", transaction)

    def check_budget_alert(self, category: str) -> dict | None:
        """Check if a category is approaching or exceeding its budget."""
        limits = self.long_term.get_budget_limits()
        if category not in limits:
            return None

        if self.long_term.spending_history:
            latest = max(t["date"] for t in self.long_term.spending_history)
            latest_dt = datetime.strptime(latest, "%Y-%m-%d")
            start = latest_dt.strftime("%Y-%m-01")
            end = latest_dt.strftime("%Y-%m-%d")
        else:
            now = datetime.now()
            start = now.strftime("%Y-%m-01")
            end = now.strftime("%Y-%m-%d")
        expenses = self.long_term.get_spending_by_category(category, start, end)
        total = sum(e["amount"] for e in expenses)
        limit = limits[category]
        percentage = (total / limit) * 100 if limit > 0 else 0

        threshold = self.long_term.preferences.get("alert_threshold_percentage", 80)

        if percentage >= 100:
            alert = {
                "category": category,
                "message": f"OVER BUDGET: {category} spending ${total:.2f} exceeds limit ${limit:.2f} ({percentage:.1f}%)",
                "severity": "critical",
            }
            self.short_term.add_alert(category, alert["message"], "critical")
            return alert
        elif percentage >= threshold:
            alert = {
                "category": category,
                "message": f"WARNING: {category} spending ${total:.2f} is at {percentage:.1f}% of ${limit:.2f} limit",
                "severity": "warning",
            }
            self.short_term.add_alert(category, alert["message"], "warning")
            return alert
        return None

    def save_all(self):
        """Persist all memory."""
        self.long_term.save()

    def get_full_context(self) -> dict:
        """Get a complete memory context for agent decision-making."""
        return {
            "short_term": self.short_term.get_context_summary(),
            "budget_limits": self.long_term.get_budget_limits(),
            "monthly_income": self.long_term.get_monthly_income(),
            "financial_goals": self.long_term.financial_goals,
            "preferences": self.long_term.preferences,
            "total_transactions": len(self.long_term.spending_history),
        }
