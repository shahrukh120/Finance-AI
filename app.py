"""
Flask Web Application for Personal Finance Manager.
Provides a beautiful dashboard UI around the multi-agent system.
"""

import io
import json
import os
import uuid
import threading
from collections import defaultdict
from datetime import datetime, timedelta

import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response, send_file
from flask_login import LoginManager, login_required, current_user
from dotenv import load_dotenv

from models import db, User, Expense, Income, Budget, Goal
from auth import auth_bp
from memory.memory_system import MemoryManager
from utils.currency import convert, get_symbol, currency_choices, CURRENCIES
from tools.financial_tools import (
    set_tool_user,
    _load_expenses,
    _load_user_profile,
    _get_latest_month,
    _detect_recurring,
    _compute_monthly_history,
    _compute_rolling_average,
    check_budget_status,
    predict_month_end_spending,
    detect_recurring_transactions,
    find_savings_opportunities,
    generate_spending_report,
)

load_dotenv()

# ─── App Factory ─────────────────────────────────────────────────────────────

app = Flask(__name__)
config_class = "config.ProductionConfig" if os.environ.get("RENDER") else "config.DevelopmentConfig"
app.config.from_object(config_class)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"

# Register blueprints
app.register_blueprint(auth_bp)

# Create tables on first run
with app.app_context():
    db.create_all()

    # SQLite-only lightweight auto-migration for local dev
    _uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if _uri.startswith("sqlite"):
        import sqlite3 as _sqlite3
        _db_path = _uri.replace("sqlite:///", "")
        if _db_path and not _db_path.startswith(":"):
            try:
                _conn = _sqlite3.connect(_db_path)
                _cur = _conn.cursor()
                _existing = {r[1] for r in _cur.execute("PRAGMA table_info(expenses)").fetchall()}
                if "original_currency" not in _existing:
                    _cur.execute("ALTER TABLE expenses ADD COLUMN original_currency VARCHAR(10) DEFAULT 'USD'")
                if "original_amount" not in _existing:
                    _cur.execute("ALTER TABLE expenses ADD COLUMN original_amount FLOAT")
                _conn.commit()
                _conn.close()
            except Exception:
                pass


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ─── Set user context for tools before each request ─────────────────────────

@app.before_request
def set_user_context():
    if current_user.is_authenticated:
        set_tool_user(current_user.id)


# In-memory store for background analysis tasks
analysis_tasks = {}


CATEGORY_COLORS = {
    "food": {"bg": "#10b981", "badge": "success"},
    "transport": {"bg": "#3b82f6", "badge": "primary"},
    "entertainment": {"bg": "#8b5cf6", "badge": "purple"},
    "bills": {"bg": "#f59e0b", "badge": "warning"},
    "healthcare": {"bg": "#ef4444", "badge": "danger"},
}

CATEGORY_ICONS = {
    "food": "fa-utensils",
    "transport": "fa-car",
    "entertainment": "fa-gamepad",
    "bills": "fa-file-invoice-dollar",
    "healthcare": "fa-heart-pulse",
}

INCOME_SOURCES = {
    "salary":      {"label": "Salary / Wages",     "icon": "fa-briefcase",      "color": "#10b981"},
    "freelance":   {"label": "Freelance / Contract","icon": "fa-laptop-code",    "color": "#3b82f6"},
    "business":    {"label": "Business Revenue",    "icon": "fa-store",          "color": "#8b5cf6"},
    "investment":  {"label": "Investments / Dividends","icon": "fa-chart-line",  "color": "#f59e0b"},
    "rental":      {"label": "Rental Income",       "icon": "fa-house",          "color": "#06b6d4"},
    "gift":        {"label": "Gift / Bonus",        "icon": "fa-gift",           "color": "#ec4899"},
    "refund":      {"label": "Refund / Cashback",   "icon": "fa-rotate-left",    "color": "#14b8a6"},
    "side_hustle": {"label": "Side Hustle",         "icon": "fa-hammer",         "color": "#f97316"},
    "other":       {"label": "Other Income",        "icon": "fa-ellipsis",       "color": "#6b7280"},
}


# ─── Routes ───────────────────────────────────────────────────────────────────


@app.route("/")
@login_required
def dashboard():
    mm = MemoryManager(user_id=current_user.id)
    profile = _load_user_profile()

    # Budget status for each category
    categories = list(profile.get("budget_limits", {}).keys())
    if not categories:
        categories = ["food", "transport", "entertainment", "bills", "healthcare"]

    budget_statuses = []
    for cat in categories:
        status = json.loads(check_budget_status.run(category=cat))
        status["color"] = CATEGORY_COLORS.get(cat, {"bg": "#6b7280"})["bg"]
        status["badge"] = CATEGORY_COLORS.get(cat, {"badge": "secondary"})["badge"]
        status["icon"] = CATEGORY_ICONS.get(cat, "fa-tag")
        budget_statuses.append(status)

    # Budget alerts
    alerts = []
    for cat in categories:
        alert = mm.check_budget_alert(cat)
        if alert:
            alerts.append(alert)

    # Financial goals
    goals = profile.get("financial_goals", [])
    for goal in goals:
        target = goal["target_amount"]
        current = goal["current_amount"]
        goal["percentage"] = round((current / target) * 100, 1) if target > 0 else 0

    # Recent transactions (last 10, sorted by date desc)
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).limit(10).all()
    recent = []
    for e in expenses:
        cur = e.original_currency or "USD"
        orig_amt = e.original_amount if e.original_amount is not None else e.amount
        sym = get_symbol(cur)
        recent.append({
            "id": e.id,
            "date": e.date.strftime("%Y-%m-%d"),
            "category": e.category,
            "amount_usd": e.amount,
            "display_amount": orig_amt,
            "display_symbol": sym,
            "display_currency": cur,
            "is_foreign": cur != "USD",
            "description": e.description or "",
        })

    # Chart data
    chart_data = {
        "labels": [s["category"].title() for s in budget_statuses],
        "values": [s["total_spent"] for s in budget_statuses],
        "budgets": [s["budget_limit"] for s in budget_statuses],
        "colors": [CATEGORY_COLORS.get(cat, {"bg": "#6b7280"})["bg"] for cat in categories],
    }

    total_spent = sum(s["total_spent"] for s in budget_statuses)
    total_budget = sum(s["budget_limit"] for s in budget_statuses)

    # ─── Monthly Income from actual inflows ───────────────────────────
    # Use the latest month (same anchor as expenses) to compute income
    all_user_expenses = Expense.query.filter_by(user_id=current_user.id).all()
    if all_user_expenses:
        anchor_date = max(e.date for e in all_user_expenses)
    else:
        anchor_date = datetime.now().date()

    income_month_start = anchor_date.replace(day=1)
    if anchor_date.month == 12:
        income_month_end = anchor_date.replace(year=anchor_date.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        income_month_end = anchor_date.replace(month=anchor_date.month + 1, day=1) - timedelta(days=1)

    monthly_incomes = Income.query.filter(
        Income.user_id == current_user.id,
        Income.date >= income_month_start,
        Income.date <= income_month_end,
    ).all()

    income = round(sum(i.amount for i in monthly_incomes), 2)
    expected_income = profile.get("monthly_income", 0)

    # Build recent inflows for the dashboard
    recent_incomes_raw = Income.query.filter_by(user_id=current_user.id).order_by(Income.date.desc()).limit(5).all()
    recent_incomes = []
    for i in recent_incomes_raw:
        cur = i.original_currency or "USD"
        orig_amt = i.original_amount if i.original_amount is not None else i.amount
        sym = get_symbol(cur)
        src = INCOME_SOURCES.get(i.source, INCOME_SOURCES["other"])
        recent_incomes.append({
            "id": i.id,
            "date": i.date.strftime("%Y-%m-%d"),
            "source": i.source,
            "source_label": src["label"],
            "source_icon": src["icon"],
            "source_color": src["color"],
            "amount_usd": i.amount,
            "display_amount": orig_amt,
            "display_symbol": sym,
            "display_currency": cur,
            "is_foreign": cur != "USD",
            "description": i.description or "",
        })

    # Income breakdown by source for the current month
    income_by_source = defaultdict(float)
    for i in monthly_incomes:
        income_by_source[i.source] += i.amount
    income_breakdown = {
        "sources": [
            {
                "source": src,
                "label": INCOME_SOURCES.get(src, INCOME_SOURCES["other"])["label"],
                "icon": INCOME_SOURCES.get(src, INCOME_SOURCES["other"])["icon"],
                "color": INCOME_SOURCES.get(src, INCOME_SOURCES["other"])["color"],
                "amount": round(amt, 2),
            }
            for src, amt in sorted(income_by_source.items(), key=lambda x: -x[1])
        ],
        "total": round(income, 2),
        "count": len(monthly_incomes),
    }

    # ─── Weekly / Monthly Spending Trend ────────────────────────────────
    view_mode = request.args.get("view", "weekly")  # "weekly" or "monthly"

    if view_mode == "monthly":
        # Show the full month containing the anchor date
        view_start = anchor_date.replace(day=1)
        if anchor_date.month == 12:
            view_end = anchor_date.replace(year=anchor_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            view_end = anchor_date.replace(month=anchor_date.month + 1, day=1) - timedelta(days=1)
        view_label = anchor_date.strftime("%B %Y")
    else:
        # Show the 7-day window ending on the anchor date
        view_end = anchor_date
        view_start = anchor_date - timedelta(days=6)
        view_label = f"{view_start.strftime('%b %d')} - {view_end.strftime('%b %d, %Y')}"

    # Query expenses in the view range
    view_expenses = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.date >= view_start,
        Expense.date <= view_end,
    ).all()

    # Build daily totals and per-category daily totals
    daily_totals = defaultdict(float)
    daily_by_category = defaultdict(lambda: defaultdict(float))
    for e in view_expenses:
        day_str = e.date.strftime("%Y-%m-%d")
        daily_totals[day_str] += e.amount
        daily_by_category[e.category][day_str] += e.amount

    # Generate all dates in range for a continuous x-axis
    trend_dates = []
    d = view_start
    while d <= view_end:
        trend_dates.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)

    # Short labels for x-axis
    trend_labels = []
    for ds in trend_dates:
        dt = datetime.strptime(ds, "%Y-%m-%d")
        trend_labels.append(dt.strftime("%b %d"))

    # Total daily spending line
    trend_values = [round(daily_totals.get(ds, 0), 2) for ds in trend_dates]

    # Per-category stacked datasets
    trend_category_datasets = []
    for cat in categories:
        cat_values = [round(daily_by_category[cat].get(ds, 0), 2) for ds in trend_dates]
        trend_category_datasets.append({
            "label": cat.title(),
            "data": cat_values,
            "color": CATEGORY_COLORS.get(cat, {"bg": "#6b7280"})["bg"],
        })

    # Summary stats for the view period
    view_total = sum(trend_values)
    view_avg_daily = round(view_total / max(len(trend_dates), 1), 2)
    view_tx_count = len(view_expenses)

    trend_data = {
        "labels": trend_labels,
        "values": trend_values,
        "category_datasets": trend_category_datasets,
        "view_total": round(view_total, 2),
        "view_avg_daily": view_avg_daily,
        "view_tx_count": view_tx_count,
        "view_label": view_label,
    }

    # ─── Committed vs Discretionary Spend ──────────────────────────────
    all_expenses_dicts = _load_expenses()
    recurring_items = _detect_recurring(all_expenses_dicts)
    committed_total = round(sum(r["monthly_cost"] for r in recurring_items), 2)
    discretionary_total = round(total_spent - committed_total, 2)

    committed_data = {
        "committed_total": committed_total,
        "discretionary_total": max(discretionary_total, 0),
        "committed_pct": round(committed_total / income * 100, 1) if income > 0 else 0,
        "discretionary_pct": round(max(discretionary_total, 0) / income * 100, 1) if income > 0 else 0,
        "recurring": recurring_items,
    }

    # ─── Budget Forecast & Rolling Average ────────────────────────────
    forecast_items = []
    for cat in categories:
        proj = json.loads(predict_month_end_spending.run(category=cat))
        proj["color"] = CATEGORY_COLORS.get(cat, {"bg": "#6b7280"})["bg"]
        proj["icon"] = CATEGORY_ICONS.get(cat, "fa-tag")
        forecast_items.append(proj)

    # Monthly history across all categories for trend chart
    history = _compute_monthly_history(all_expenses_dicts, categories)
    history_datasets = []
    for cat in categories:
        cat_vals = [history["by_category"].get(cat, {}).get(m, 0) for m in history["months"]]
        rolling = _compute_rolling_average(cat_vals)
        history_datasets.append({
            "category": cat,
            "label": cat.title(),
            "values": cat_vals,
            "rolling_avg": rolling,
            "color": CATEGORY_COLORS.get(cat, {"bg": "#6b7280"})["bg"],
        })

    # Overall monthly totals + rolling average
    overall_vals = [history["totals"].get(m, 0) for m in history["months"]]
    overall_rolling = _compute_rolling_average(overall_vals)

    forecast_data = {
        "forecast_items": forecast_items,
        "months": history["months"],
        "month_labels": [
            datetime.strptime(m, "%Y-%m").strftime("%b %Y") for m in history["months"]
        ],
        "overall_values": overall_vals,
        "overall_rolling_avg": overall_rolling,
        "category_datasets": history_datasets,
    }

    return render_template(
        "dashboard.html",
        budget_statuses=budget_statuses,
        alerts=alerts,
        goals=goals,
        recent=recent,
        chart_data=chart_data,
        total_spent=total_spent,
        total_budget=total_budget,
        income=income,
        expected_income=expected_income,
        profile=profile,
        category_colors=CATEGORY_COLORS,
        view_mode=view_mode,
        trend_data=trend_data,
        committed_data=committed_data,
        forecast_data=forecast_data,
        recent_incomes=recent_incomes,
        income_breakdown=income_breakdown,
        income_sources=INCOME_SOURCES,
    )


@app.route("/add-expense", methods=["GET", "POST"])
@login_required
def add_expense():
    if request.method == "POST":
        category = request.form.get("category", "").strip()
        amount_str = request.form.get("amount", "0")
        description = request.form.get("description", "").strip()
        date_str = request.form.get("date", "")
        currency_code = request.form.get("currency", "USD").strip().upper()

        # Validate
        valid_cats = ["food", "transport", "entertainment", "bills", "healthcare"]
        if category not in valid_cats:
            flash("Invalid category.", "danger")
            return redirect(url_for("add_expense"))

        try:
            original_amount = round(float(amount_str), 2)
            if original_amount <= 0:
                raise ValueError
        except ValueError:
            flash("Amount must be a positive number.", "danger")
            return redirect(url_for("add_expense"))

        if currency_code not in CURRENCIES:
            flash("Invalid currency selected.", "danger")
            return redirect(url_for("add_expense"))

        if not description:
            flash("Description is required.", "danger")
            return redirect(url_for("add_expense"))

        # Parse date
        try:
            expense_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.now().date()
        except ValueError:
            expense_date = datetime.now().date()

        # Convert to USD for storage
        amount_usd = convert(original_amount, currency_code, "USD")

        # Save to database
        expense = Expense(
            user_id=current_user.id,
            date=expense_date,
            category=category,
            amount=amount_usd,
            description=description,
            original_currency=currency_code,
            original_amount=original_amount,
        )
        db.session.add(expense)
        db.session.commit()

        symbol = get_symbol(currency_code)
        if currency_code == "USD":
            flash(f"Expense added: ${amount_usd:.2f} for {category} - {description}", "success")
        else:
            flash(
                f"Expense added: {symbol}{original_amount:,.2f} {currency_code} "
                f"(${amount_usd:.2f} USD) for {category} - {description}",
                "success",
            )
        return redirect(url_for("dashboard"))

    # Build a {code: rate_to_usd} dict for the JS conversion preview
    rates_for_js = {code: info[2] for code, info in CURRENCIES.items()}
    return render_template("add_expense.html", currencies=currency_choices(), currency_rates=rates_for_js)


@app.route("/analysis")
@login_required
def analysis():
    return render_template("analysis.html")


@app.route("/api/run-analysis", methods=["POST"])
@login_required
def run_analysis():
    data = request.get_json() or {}
    pattern = data.get("pattern", "sequential")
    task_id = str(uuid.uuid4())
    user_id = current_user.id

    analysis_tasks[task_id] = {"status": "running", "result": None, "error": None}

    def run_in_background(tid, pat, uid):
        with app.app_context():
            set_tool_user(uid)
            try:
                from main import run_sequential, run_hierarchical
                if pat == "hierarchical":
                    result = run_hierarchical()
                else:
                    result = run_sequential()
                analysis_tasks[tid]["status"] = "complete"
                analysis_tasks[tid]["result"] = str(result)
            except Exception as e:
                analysis_tasks[tid]["status"] = "error"
                analysis_tasks[tid]["error"] = str(e)

    thread = threading.Thread(target=run_in_background, args=(task_id, pattern, user_id))
    thread.daemon = True
    thread.start()

    return jsonify({"task_id": task_id})


@app.route("/api/analysis-status/<task_id>")
@login_required
def analysis_status(task_id):
    task = analysis_tasks.get(task_id)
    if not task:
        return jsonify({"status": "not_found"}), 404
    return jsonify(task)


@app.route("/delete-expense/<int:expense_id>", methods=["POST"])
@login_required
def delete_expense(expense_id):
    expense = db.session.get(Expense, expense_id)
    if not expense:
        flash("Expense not found.", "danger")
        return redirect(url_for("dashboard"))
    if expense.user_id != current_user.id:
        flash("You can only delete your own expenses.", "danger")
        return redirect(url_for("dashboard"))
    description = expense.description
    category = expense.category
    cur = expense.original_currency or "USD"
    sym = get_symbol(cur)
    display_amt = expense.original_amount if expense.original_amount is not None else expense.amount
    db.session.delete(expense)
    db.session.commit()
    flash(f"Deleted: {sym}{display_amt:,.2f} {cur} for {category} - {description}", "info")
    return redirect(url_for("dashboard"))


@app.route("/add-income", methods=["GET", "POST"])
@login_required
def add_income():
    if request.method == "POST":
        source = request.form.get("source", "").strip()
        amount_str = request.form.get("amount", "0")
        description = request.form.get("description", "").strip()
        date_str = request.form.get("date", "")
        currency_code = request.form.get("currency", "USD").strip().upper()

        if source not in INCOME_SOURCES:
            flash("Invalid income source.", "danger")
            return redirect(url_for("add_income"))

        try:
            original_amount = round(float(amount_str), 2)
            if original_amount <= 0:
                raise ValueError
        except ValueError:
            flash("Amount must be a positive number.", "danger")
            return redirect(url_for("add_income"))

        if currency_code not in CURRENCIES:
            flash("Invalid currency selected.", "danger")
            return redirect(url_for("add_income"))

        if not description:
            flash("Description is required.", "danger")
            return redirect(url_for("add_income"))

        try:
            income_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.now().date()
        except ValueError:
            income_date = datetime.now().date()

        amount_usd = convert(original_amount, currency_code, "USD")

        inc = Income(
            user_id=current_user.id,
            date=income_date,
            source=source,
            amount=amount_usd,
            description=description,
            original_currency=currency_code,
            original_amount=original_amount,
        )
        db.session.add(inc)
        db.session.commit()

        symbol = get_symbol(currency_code)
        src_label = INCOME_SOURCES[source]["label"]
        if currency_code == "USD":
            flash(f"Income added: ${amount_usd:.2f} — {src_label} — {description}", "success")
        else:
            flash(
                f"Income added: {symbol}{original_amount:,.2f} {currency_code} "
                f"(${amount_usd:.2f} USD) — {src_label} — {description}",
                "success",
            )
        return redirect(url_for("dashboard"))

    rates_for_js = {code: info[2] for code, info in CURRENCIES.items()}
    return render_template(
        "add_income.html",
        currencies=currency_choices(),
        currency_rates=rates_for_js,
        income_sources=INCOME_SOURCES,
    )


@app.route("/delete-income/<int:income_id>", methods=["POST"])
@login_required
def delete_income(income_id):
    inc = db.session.get(Income, income_id)
    if not inc:
        flash("Income entry not found.", "danger")
        return redirect(url_for("dashboard"))
    if inc.user_id != current_user.id:
        flash("You can only delete your own income entries.", "danger")
        return redirect(url_for("dashboard"))
    cur = inc.original_currency or "USD"
    sym = get_symbol(cur)
    display_amt = inc.original_amount if inc.original_amount is not None else inc.amount
    src_label = INCOME_SOURCES.get(inc.source, INCOME_SOURCES["other"])["label"]
    db.session.delete(inc)
    db.session.commit()
    flash(f"Deleted income: {sym}{display_amt:,.2f} {cur} — {src_label}", "info")
    return redirect(url_for("dashboard"))


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        monthly_income = request.form.get("monthly_income", "0")
        alert_threshold = request.form.get("alert_threshold", "80")
        savings_rate = request.form.get("savings_rate", "20")

        if name:
            current_user.name = name
        try:
            current_user.monthly_income = round(float(monthly_income), 2)
        except ValueError:
            pass
        try:
            current_user.alert_threshold_percentage = int(alert_threshold)
        except ValueError:
            pass
        try:
            current_user.preferred_savings_rate = int(savings_rate)
        except ValueError:
            pass

        db.session.commit()
        flash("Settings updated successfully.", "success")
        return redirect(url_for("settings"))

    return render_template("settings.html")


@app.route("/api/budget-status")
@login_required
def api_budget_status():
    categories = ["food", "transport", "entertainment", "bills", "healthcare"]
    results = {}
    for cat in categories:
        results[cat] = json.loads(check_budget_status.run(category=cat))
    return jsonify(results)


# ─── Export Routes ────────────────────────────────────────────────────────────


@app.route("/export/csv")
@login_required
def export_csv():
    """Download all user expenses as a CSV file."""
    expenses = (
        Expense.query
        .filter_by(user_id=current_user.id)
        .order_by(Expense.date.desc())
        .all()
    )

    rows = [
        {
            "Date": e.date.strftime("%Y-%m-%d"),
            "Category": e.category.title(),
            "Amount (USD)": e.amount,
            "Original Amount": e.original_amount if e.original_amount is not None else e.amount,
            "Currency": e.original_currency or "USD",
            "Description": e.description or "",
        }
        for e in expenses
    ]

    columns = ["Date", "Category", "Amount (USD)", "Original Amount", "Currency", "Description"]
    df = pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame(columns=columns)

    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)

    filename = f"expenses_{current_user.username}_{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.route("/export/pdf")
@login_required
def export_pdf():
    """Generate a comprehensive financial report as a downloadable PDF."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    profile = _load_user_profile()
    all_expenses_dicts = _load_expenses()
    income = profile.get("monthly_income", 0)

    # Gather income entries for the report
    pdf_incomes = Income.query.filter_by(user_id=current_user.id).order_by(Income.date.desc()).limit(20).all()

    categories = list(profile.get("budget_limits", {}).keys()) or [
        "food", "transport", "entertainment", "bills", "healthcare"
    ]

    # ── Gather data ──────────────────────────────────────────────────
    budget_statuses = []
    for cat in categories:
        bs = json.loads(check_budget_status.run(category=cat))
        budget_statuses.append(bs)

    forecast_items = []
    for cat in categories:
        proj = json.loads(predict_month_end_spending.run(category=cat))
        forecast_items.append(proj)

    recurring_items = _detect_recurring(all_expenses_dicts)
    committed_total = round(sum(r["monthly_cost"] for r in recurring_items), 2)
    total_spent = sum(bs["total_spent"] for bs in budget_statuses)
    total_budget = sum(bs["budget_limit"] for bs in budget_statuses)

    savings_raw = json.loads(find_savings_opportunities.run(spending_data="all"))

    # ── Build PDF ────────────────────────────────────────────────────
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=20 * mm, bottomMargin=15 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
    )
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Heading1"],
        fontSize=20, spaceAfter=4, textColor=colors.HexColor("#1e293b"),
    )
    subtitle_style = ParagraphStyle(
        "ReportSub", parent=styles["Normal"],
        fontSize=10, textColor=colors.HexColor("#64748b"), spaceAfter=12,
    )
    section_style = ParagraphStyle(
        "SectionHead", parent=styles["Heading2"],
        fontSize=13, spaceBefore=16, spaceAfter=6,
        textColor=colors.HexColor("#334155"),
        borderPadding=(0, 0, 4, 0),
    )
    body_style = ParagraphStyle(
        "BodyText2", parent=styles["Normal"],
        fontSize=9.5, leading=13, textColor=colors.HexColor("#334155"),
    )
    right_style = ParagraphStyle(
        "RightBody", parent=body_style, alignment=TA_RIGHT,
    )

    elements = []

    # ── Header ──────────────────────────────
    elements.append(Paragraph("FinanceAI — Financial Report", title_style))
    elements.append(Paragraph(
        f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} for "
        f"<b>{current_user.name}</b> ({current_user.email})",
        subtitle_style,
    ))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
    elements.append(Spacer(1, 6))

    # ── Summary ─────────────────────────────
    elements.append(Paragraph("Summary", section_style))
    summary_data = [
        ["Monthly Inflow", f"${income:,.2f}"],
        ["Total Spent (Current Month)", f"${total_spent:,.2f}"],
        ["Total Budget", f"${total_budget:,.2f}"],
        ["Remaining", f"${income - total_spent:,.2f}"],
        ["Budget Utilization", f"{total_spent / total_budget * 100:.0f}%" if total_budget > 0 else "N/A"],
        ["Committed (Recurring)", f"${committed_total:,.2f}"],
        ["Discretionary", f"${max(total_spent - committed_total, 0):,.2f}"],
    ]
    t = Table(summary_data, colWidths=[120 * mm, 50 * mm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#334155")),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 6))

    # ── Income Entries ──────────────────────
    if pdf_incomes:
        elements.append(Paragraph("Money Inflows", section_style))
        inc_data = [["Date", "Source", "Description", "USD", "Original"]]
        for i in pdf_incomes:
            src_label = INCOME_SOURCES.get(i.source, INCOME_SOURCES["other"])["label"]
            orig_cur = i.original_currency or "USD"
            if orig_cur != "USD" and i.original_amount is not None:
                orig_str = f"{get_symbol(orig_cur)}{i.original_amount:,.2f} {orig_cur}"
            else:
                orig_str = ""
            inc_data.append([
                i.date.strftime("%Y-%m-%d"),
                src_label,
                (i.description or "")[:36],
                f"${i.amount:,.2f}",
                orig_str,
            ])
        t = Table(inc_data, colWidths=[24 * mm, 34 * mm, 46 * mm, 26 * mm, 34 * mm])
        t.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), header_bg),
            ("ALIGN", (3, 0), (4, -1), "RIGHT"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 6))

    # ── Budget Status ───────────────────────
    elements.append(Paragraph("Budget Status by Category", section_style))
    budget_table_data = [["Category", "Spent", "Budget", "% Used", "Status"]]
    for bs in budget_statuses:
        budget_table_data.append([
            bs["category"].title(),
            f"${bs['total_spent']:,.2f}",
            f"${bs['budget_limit']:,.2f}",
            f"{bs['percentage_used']:.0f}%",
            bs["status"].replace("_", " "),
        ])
    t = Table(budget_table_data, colWidths=[35 * mm, 30 * mm, 30 * mm, 25 * mm, 40 * mm])
    header_bg = colors.HexColor("#f1f5f9")
    over_color = colors.HexColor("#ef4444")
    ok_color = colors.HexColor("#334155")
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (4, 0), (4, -1), "CENTER"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    # Highlight over-budget rows
    for i, bs in enumerate(budget_statuses, start=1):
        if bs["status"] == "OVER_BUDGET":
            t.setStyle(TableStyle([
                ("TEXTCOLOR", (0, i), (-1, i), over_color),
                ("FONTNAME", (4, i), (4, i), "Helvetica-Bold"),
            ]))
    elements.append(t)
    elements.append(Spacer(1, 6))

    # ── Forecast ────────────────────────────
    elements.append(Paragraph("Month-End Forecast", section_style))
    fc_data = [["Category", "Current", "Projected", "Burn/Day", "3mo Avg", "Trend"]]
    for fi in forecast_items:
        ravg = f"${fi['rolling_avg_3m']:,.0f}" if fi.get("rolling_avg_3m") is not None else "—"
        fc_data.append([
            fi["category"].title(),
            f"${fi['current_total']:,.2f}",
            f"${fi['projected_month_end_total']:,.2f}",
            f"${fi['daily_burn_rate']:,.2f}",
            ravg,
            fi["trend"].replace("_", " ").title(),
        ])
    t = Table(fc_data, colWidths=[28 * mm, 27 * mm, 27 * mm, 24 * mm, 24 * mm, 30 * mm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (5, 0), (5, -1), "CENTER"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 6))

    # ── Recurring Charges ───────────────────
    if recurring_items:
        elements.append(Paragraph("Detected Recurring Charges", section_style))
        rec_data = [["Description", "Category", "Monthly Cost", "Confidence"]]
        for r in recurring_items:
            rec_data.append([
                r["description"],
                r["category"].title(),
                f"${r['monthly_cost']:,.2f}",
                r["confidence"].upper(),
            ])
        rec_data.append(["", "", f"${committed_total:,.2f}", "TOTAL"])
        t = Table(rec_data, colWidths=[60 * mm, 30 * mm, 35 * mm, 30 * mm])
        t.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), header_bg),
            ("ALIGN", (2, 0), (2, -1), "RIGHT"),
            ("ALIGN", (3, 0), (3, -1), "CENTER"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#94a3b8")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 6))

    # ── Savings Opportunities ───────────────
    opps = savings_raw.get("opportunities", [])
    if opps:
        elements.append(Paragraph("Savings Opportunities", section_style))
        for i, opp in enumerate(opps, 1):
            elements.append(Paragraph(
                f"<b>{i}. {opp.get('type', 'Tip').replace('_', ' ').title()}</b> — {opp.get('suggestion', '')}",
                body_style,
            ))
            if opp.get("potential_savings"):
                elements.append(Paragraph(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;Potential savings: <b>${opp['potential_savings']:,.2f}/mo</b>",
                    body_style,
                ))
            elements.append(Spacer(1, 3))
        elements.append(Spacer(1, 6))

    # ── Recent Transactions (last 25) ───────
    elements.append(Paragraph("Recent Transactions", section_style))
    recent_expenses = (
        Expense.query
        .filter_by(user_id=current_user.id)
        .order_by(Expense.date.desc())
        .limit(25)
        .all()
    )
    tx_data = [["Date", "Category", "Description", "USD", "Original"]]
    for e in recent_expenses:
        orig_cur = e.original_currency or "USD"
        if orig_cur != "USD" and e.original_amount is not None:
            orig_str = f"{get_symbol(orig_cur)}{e.original_amount:,.2f} {orig_cur}"
        else:
            orig_str = ""
        tx_data.append([
            e.date.strftime("%Y-%m-%d"),
            e.category.title(),
            (e.description or "")[:36],
            f"${e.amount:,.2f}",
            orig_str,
        ])
    t = Table(tx_data, colWidths=[24 * mm, 24 * mm, 55 * mm, 26 * mm, 35 * mm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("ALIGN", (3, 0), (4, -1), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(t)

    # ── Footer ──────────────────────────────
    elements.append(Spacer(1, 16))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1")))
    elements.append(Spacer(1, 4))
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"],
        fontSize=7.5, textColor=colors.HexColor("#94a3b8"), alignment=TA_CENTER,
    )
    elements.append(Paragraph(
        "FinanceAI — Personal Finance Manager powered by CrewAI + Groq (Llama 3.3 70B)",
        footer_style,
    ))

    doc.build(elements)
    buf.seek(0)

    filename = f"finance_report_{current_user.username}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return send_file(
        buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=5000)
