"""
Seed data for new user accounts.
Reads the original JSON data files and inserts sample expenses, budgets, and goals.
"""

import json
import os
from datetime import datetime

from models import Budget, Expense, Goal, db

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def seed_user_data(user):
    """Populate a newly registered user with sample data."""
    # Seed budget limits
    profile_path = os.path.join(DATA_DIR, "user_profile.json")
    if os.path.exists(profile_path):
        with open(profile_path, "r") as f:
            profile = json.load(f)

        for category, limit_amount in profile.get("budget_limits", {}).items():
            db.session.add(Budget(user_id=user.id, category=category, limit_amount=limit_amount))

        for goal_data in profile.get("financial_goals", []):
            target_date = None
            if goal_data.get("target_date"):
                target_date = datetime.strptime(goal_data["target_date"], "%Y-%m-%d").date()
            db.session.add(Goal(
                user_id=user.id,
                name=goal_data["name"],
                target_amount=goal_data["target_amount"],
                current_amount=goal_data.get("current_amount", 0),
                target_date=target_date,
            ))

    # Seed sample expenses
    expenses_path = os.path.join(DATA_DIR, "sample_expenses.json")
    if os.path.exists(expenses_path):
        with open(expenses_path, "r") as f:
            expenses = json.load(f)

        for exp in expenses:
            db.session.add(Expense(
                user_id=user.id,
                date=datetime.strptime(exp["date"], "%Y-%m-%d").date(),
                category=exp["category"],
                amount=exp["amount"],
                description=exp.get("description", ""),
            ))

    db.session.commit()
