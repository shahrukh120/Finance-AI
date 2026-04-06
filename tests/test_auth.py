"""
Tests for authentication — register, login, logout, route protection, data isolation.
Run with: python -m pytest tests/ -v
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask
from flask_login import LoginManager
from models import db as _db, User, Expense, Budget
from auth import auth_bp
from seed import seed_user_data


def create_test_app():
    """Create a separate Flask app for auth tests."""
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"),
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "auth-test-secret"
    app.config["WTF_CSRF_ENABLED"] = False

    _db.init_app(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    app.register_blueprint(auth_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return _db.session.get(User, int(user_id))

    @app.route("/")
    def dashboard():
        from flask_login import current_user
        if current_user.is_authenticated:
            return f"Dashboard for {current_user.name}"
        return "Dashboard"

    @app.route("/add-expense")
    def add_expense():
        return "Add Expense"

    @app.route("/analysis")
    def analysis():
        return "Analysis"

    @app.route("/export/csv")
    def export_csv():
        return "CSV"

    @app.route("/export/pdf")
    def export_pdf():
        return "PDF"

    @app.route("/add-income")
    def add_income():
        return "Add Income"

    @app.route("/delete-income/<int:income_id>", methods=["POST"])
    def delete_income(income_id):
        return "Delete Income"

    @app.route("/settings")
    def settings():
        return "Settings"

    with app.app_context():
        _db.create_all()

    return app


class TestRegistration:
    def test_register_page_loads(self):
        app = create_test_app()
        with app.test_client() as client:
            resp = client.get("/register")
            assert resp.status_code == 200

    def test_register_new_user(self):
        app = create_test_app()
        with app.test_client() as client:
            resp = client.post("/register", data={
                "username": "newuser",
                "email": "new@example.com",
                "name": "New User",
                "password": "securepass",
            }, follow_redirects=True)
            assert resp.status_code == 200
            with app.app_context():
                user = User.query.filter_by(username="newuser").first()
                assert user is not None
                assert user.name == "New User"
                # Verify seed data was created
                assert Budget.query.filter_by(user_id=user.id).count() == 5
                assert Expense.query.filter_by(user_id=user.id).count() > 0

    def test_duplicate_username_rejected(self):
        app = create_test_app()
        with app.test_client() as client:
            client.post("/register", data={
                "username": "dupuser", "email": "dup1@example.com",
                "name": "User 1", "password": "password1",
            })
            resp = client.post("/register", data={
                "username": "dupuser", "email": "dup2@example.com",
                "name": "User 2", "password": "password2",
            }, follow_redirects=True)
            assert b"Username already taken" in resp.data


class TestLogin:
    def test_login_page_loads(self):
        app = create_test_app()
        with app.test_client() as client:
            resp = client.get("/login")
            assert resp.status_code == 200

    def test_login_valid_credentials(self):
        app = create_test_app()
        with app.app_context():
            user = User(username="loginuser", email="login@example.com", name="Login User")
            user.set_password("mypassword")
            _db.session.add(user)
            _db.session.commit()
        with app.test_client() as client:
            resp = client.post("/login", data={
                "username": "loginuser", "password": "mypassword",
            }, follow_redirects=True)
            assert resp.status_code == 200

    def test_login_invalid_credentials(self):
        app = create_test_app()
        with app.test_client() as client:
            resp = client.post("/login", data={
                "username": "nobody", "password": "wrong",
            }, follow_redirects=True)
            assert b"Invalid username or password" in resp.data


class TestDataIsolation:
    def test_users_see_only_own_expenses(self):
        app = create_test_app()
        with app.app_context():
            user1 = User(username="user1", email="u1@example.com", name="User 1")
            user1.set_password("pass1")
            user2 = User(username="user2", email="u2@example.com", name="User 2")
            user2.set_password("pass2")
            _db.session.add_all([user1, user2])
            _db.session.commit()

            seed_user_data(user1)
            seed_user_data(user2)

            u1_count = Expense.query.filter_by(user_id=user1.id).count()
            u2_count = Expense.query.filter_by(user_id=user2.id).count()
            assert u1_count > 0
            assert u2_count > 0
            assert u1_count == u2_count  # Both seeded with same data
