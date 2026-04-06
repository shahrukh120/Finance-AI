"""
Tests for CSV and PDF export routes.
Run with: python -m pytest tests/test_exports.py -v
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask
from flask_login import LoginManager
from models import db as _db, User, Expense, Budget, Goal
from auth import auth_bp
from seed import seed_user_data
from datetime import datetime


def create_export_app():
    """Create a Flask app with the real export routes wired in."""
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"),
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "export-test-secret"

    _db.init_app(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    app.register_blueprint(auth_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return _db.session.get(User, int(user_id))

    # Minimal dashboard route so base.html url_for('dashboard') works
    @app.route("/")
    def dashboard():
        return "Dashboard"

    @app.route("/add-expense")
    def add_expense():
        return "Add Expense"

    @app.route("/analysis")
    def analysis():
        return "Analysis"

    # Import and register the real export routes
    from tools.financial_tools import set_tool_user

    @app.before_request
    def _set_ctx():
        from flask_login import current_user
        if current_user.is_authenticated:
            set_tool_user(current_user.id)

    # Wire in the actual export route functions from app module
    import app as app_module
    app.add_url_rule("/export/csv", "export_csv", app_module.export_csv)
    app.add_url_rule("/export/pdf", "export_pdf", app_module.export_pdf)

    # Stubs for routes referenced by templates
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


def _login(client, username, password):
    return client.post("/login", data={
        "username": username, "password": password,
    }, follow_redirects=True)


class TestCSVExport:
    def test_csv_requires_login(self):
        app = create_export_app()
        with app.test_client() as c:
            resp = c.get("/export/csv")
            assert resp.status_code == 302  # redirect to login

    def test_csv_download(self):
        app = create_export_app()
        with app.app_context():
            user = User(username="csvuser", email="csv@test.com", name="CSV User", monthly_income=5000)
            user.set_password("pass")
            _db.session.add(user)
            _db.session.commit()
            seed_user_data(user)

        with app.test_client() as c:
            _login(c, "csvuser", "pass")
            resp = c.get("/export/csv")
            assert resp.status_code == 200
            assert resp.content_type == "text/csv; charset=utf-8"
            assert "attachment" in resp.headers.get("Content-Disposition", "")
            assert ".csv" in resp.headers.get("Content-Disposition", "")

            # Parse CSV content
            text = resp.data.decode("utf-8")
            lines = text.strip().split("\n")
            header = lines[0]
            assert "Date" in header
            assert "Amount (USD)" in header
            assert "Currency" in header
            assert len(lines) > 1  # has data rows

    def test_csv_empty_user(self):
        app = create_export_app()
        with app.app_context():
            user = User(username="emptyuser", email="empty@test.com", name="Empty User")
            user.set_password("pass")
            _db.session.add(user)
            _db.session.commit()

        with app.test_client() as c:
            _login(c, "emptyuser", "pass")
            resp = c.get("/export/csv")
            assert resp.status_code == 200
            text = resp.data.decode("utf-8")
            lines = text.strip().split("\n")
            assert "Amount (USD)" in lines[0]
            assert len(lines) == 1  # header only, no data


class TestPDFExport:
    def test_pdf_requires_login(self):
        app = create_export_app()
        with app.test_client() as c:
            resp = c.get("/export/pdf")
            assert resp.status_code == 302

    def test_pdf_download(self):
        app = create_export_app()
        with app.app_context():
            user = User(username="pdfuser", email="pdf@test.com", name="PDF User", monthly_income=5000)
            user.set_password("pass")
            _db.session.add(user)
            _db.session.commit()
            seed_user_data(user)

        with app.test_client() as c:
            _login(c, "pdfuser", "pass")
            resp = c.get("/export/pdf")
            assert resp.status_code == 200
            assert resp.content_type == "application/pdf"
            assert "attachment" in resp.headers.get("Content-Disposition", "")
            assert ".pdf" in resp.headers.get("Content-Disposition", "")

            # Verify it's actually a PDF (starts with %PDF)
            assert resp.data[:5] == b"%PDF-"

    def test_pdf_contains_content(self):
        app = create_export_app()
        with app.app_context():
            user = User(username="pdfuser2", email="pdf2@test.com", name="PDF Content User", monthly_income=5000)
            user.set_password("pass")
            _db.session.add(user)
            _db.session.commit()
            seed_user_data(user)

        with app.test_client() as c:
            _login(c, "pdfuser2", "pass")
            resp = c.get("/export/pdf")
            assert resp.status_code == 200
            # PDF should be non-trivial in size (has tables, text, etc.)
            assert len(resp.data) > 2000
