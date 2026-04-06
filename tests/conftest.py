"""
Shared pytest fixtures for database-backed tests.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime
from flask import Flask
from models import db as _db, User, Expense, Income, Budget, Goal
from tools.financial_tools import set_tool_user

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


@pytest.fixture(scope="session")
def app():
    """Create a Flask app with an in-memory SQLite database."""
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    _db.init_app(app)
    with app.app_context():
        _db.create_all()
    yield app


@pytest.fixture(scope="session")
def test_user(app):
    """Create a test user with seeded data."""
    with app.app_context():
        user = User(username="testuser", email="test@example.com", name="Test User", monthly_income=5000.0)
        user.set_password("password123")
        _db.session.add(user)
        _db.session.commit()

        # Seed budgets
        for category, limit_amount in {"food": 400, "transport": 200, "entertainment": 250, "bills": 600, "healthcare": 300}.items():
            _db.session.add(Budget(user_id=user.id, category=category, limit_amount=limit_amount))

        # Seed goals
        _db.session.add(Goal(user_id=user.id, name="Emergency Fund", target_amount=10000, current_amount=3500, target_date=datetime(2026, 12, 31).date()))
        _db.session.add(Goal(user_id=user.id, name="Vacation Fund", target_amount=3000, current_amount=800, target_date=datetime(2026, 8, 1).date()))

        # Seed expenses from JSON
        expenses_path = os.path.join(DATA_DIR, "sample_expenses.json")
        if os.path.exists(expenses_path):
            with open(expenses_path, "r") as f:
                expenses = json.load(f)
            for exp in expenses:
                _db.session.add(Expense(
                    user_id=user.id,
                    date=datetime.strptime(exp["date"], "%Y-%m-%d").date(),
                    category=exp["category"],
                    amount=exp["amount"],
                    description=exp.get("description", ""),
                ))

        # Seed sample income entries for the same month as expenses
        _db.session.add(Income(
            user_id=user.id,
            date=datetime(2026, 3, 1).date(),
            source="salary",
            amount=5000.0,
            description="Monthly salary",
        ))
        _db.session.add(Income(
            user_id=user.id,
            date=datetime(2026, 3, 15).date(),
            source="freelance",
            amount=500.0,
            description="Freelance project",
        ))

        _db.session.commit()
        yield user


@pytest.fixture(autouse=True)
def app_context(app, test_user):
    """Push app context and set tool user for every test."""
    with app.app_context():
        set_tool_user(test_user.id)
        yield
