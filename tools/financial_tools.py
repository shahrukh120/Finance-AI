"""
Financial Tools for the Personal Finance Manager Agent.

5 tools that agents can invoke to analyze and report on financial data.
Each tool is implemented as a CrewAI-compatible @tool function.

Data is loaded from the database when a user context is set (web mode),
or from JSON files as fallback (CLI mode).
"""

import contextvars
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta

from crewai.tools import tool

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

# Thread-safe user context for CrewAI tools (set via before_request hook)
_current_user_id = contextvars.ContextVar("current_user_id", default=None)


def set_tool_user(user_id):
    """Set the current user ID for tool data access. Call before running tools."""
    _current_user_id.set(user_id)


def _load_expenses() -> list[dict]:
    """Load all expenses — from DB if user context is set, else from JSON."""
    user_id = _current_user_id.get()
    if user_id is not None:
        from models import Expense
        rows = Expense.query.filter_by(user_id=user_id).all()
        return [
            {
                "id": r.id,
                "date": r.date.strftime("%Y-%m-%d"),
                "category": r.category,
                "amount": r.amount,
                "description": r.description or "",
            }
            for r in rows
        ]
    # Fallback: JSON file (CLI mode)
    path = os.path.join(DATA_DIR, "sample_expenses.json")
    with open(path, "r") as f:
        return json.load(f)


def _load_user_profile() -> dict:
    """Load user profile — from DB if user context is set, else from JSON."""
    user_id = _current_user_id.get()
    if user_id is not None:
        from models import Budget, Goal, Income, User, db
        user = db.session.get(User, user_id)
        if not user:
            return {}
        budgets = {b.category: b.limit_amount for b in Budget.query.filter_by(user_id=user_id)}
        goals = [
            {
                "name": g.name,
                "target_amount": g.target_amount,
                "current_amount": g.current_amount,
                "target_date": g.target_date.strftime("%Y-%m-%d") if g.target_date else None,
            }
            for g in Goal.query.filter_by(user_id=user_id)
        ]
        # Compute monthly income from actual inflows for the latest month
        expenses = _load_expenses()
        if expenses:
            latest_date = max(e["date"] for e in expenses)
            month_prefix = latest_date[:7]  # "YYYY-MM"
        else:
            from datetime import datetime as _dt
            month_prefix = _dt.now().strftime("%Y-%m")

        month_start = datetime.strptime(month_prefix + "-01", "%Y-%m-%d").date()
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)

        monthly_income_total = sum(
            i.amount for i in Income.query.filter(
                Income.user_id == user_id,
                Income.date >= month_start,
                Income.date <= month_end,
            )
        )
        # Fallback to user's expected income if no inflows logged
        if monthly_income_total == 0:
            monthly_income_total = user.monthly_income

        return {
            "name": user.name,
            "monthly_income": monthly_income_total,
            "expected_monthly_income": user.monthly_income,
            "currency": user.currency,
            "budget_limits": budgets,
            "financial_goals": goals,
            "preferences": {
                "alert_threshold_percentage": user.alert_threshold_percentage,
                "preferred_savings_rate": user.preferred_savings_rate,
                "report_frequency": user.report_frequency,
            },
        }
    # Fallback: JSON file (CLI mode)
    path = os.path.join(DATA_DIR, "user_profile.json")
    with open(path, "r") as f:
        return json.load(f)


def _get_latest_month(expenses: list[dict]) -> tuple[str, int, int]:
    """
    Determine the latest month present in the expense data.
    Returns (month_start_str, days_in_month, days_elapsed) based on the most recent transaction.
    """
    if not expenses:
        now = datetime.now()
        return now.strftime("%Y-%m-01"), 30, 1
    latest_date = max(datetime.strptime(e["date"], "%Y-%m-%d") for e in expenses)
    month_start = latest_date.replace(day=1)
    if month_start.month == 12:
        days_in_month = 31
    else:
        next_month = month_start.replace(month=month_start.month + 1)
        days_in_month = (next_month - month_start).days
    days_elapsed = latest_date.day
    return month_start.strftime("%Y-%m-%d"), days_in_month, days_elapsed


# ─── Tool 1: Calculate Category Total ────────────────────────────────────────


@tool("calculate_category_total")
def calculate_category_total(category: str, start_date: str, end_date: str) -> str:
    """
    Calculate the total amount spent in a given category within a date range.
    Args:
        category: Expense category (food, transport, entertainment, bills, healthcare)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    Returns:
        JSON string with total amount, transaction count, and breakdown.
    """
    expenses = _load_expenses()
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    filtered = [
        e for e in expenses
        if e["category"] == category
        and start <= datetime.strptime(e["date"], "%Y-%m-%d") <= end
    ]

    total = sum(e["amount"] for e in filtered)
    return json.dumps({
        "category": category,
        "start_date": start_date,
        "end_date": end_date,
        "total_amount": round(total, 2),
        "transaction_count": len(filtered),
        "transactions": filtered,
    }, indent=2)


# ─── Tool 2: Check Budget Status ─────────────────────────────────────────────


@tool("check_budget_status")
def check_budget_status(category: str) -> str:
    """
    Check how much of the monthly budget has been used for a given category.
    Args:
        category: Expense category (food, transport, entertainment, bills, healthcare)
    Returns:
        JSON string with budget limit, amount spent, percentage used, and status.
    """
    profile = _load_user_profile()
    expenses = _load_expenses()

    budget_limit = profile["budget_limits"].get(category, 0)

    month_start, _, _ = _get_latest_month(expenses)
    month_expenses = [
        e for e in expenses
        if e["category"] == category
        and e["date"] >= month_start
    ]
    total_spent = sum(e["amount"] for e in month_expenses)
    percentage_used = (total_spent / budget_limit * 100) if budget_limit > 0 else 0
    remaining = budget_limit - total_spent

    if percentage_used >= 100:
        status = "OVER_BUDGET"
    elif percentage_used >= 80:
        status = "WARNING"
    elif percentage_used >= 50:
        status = "ON_TRACK"
    else:
        status = "HEALTHY"

    return json.dumps({
        "category": category,
        "budget_limit": budget_limit,
        "total_spent": round(total_spent, 2),
        "remaining": round(remaining, 2),
        "percentage_used": round(percentage_used, 1),
        "status": status,
        "transaction_count": len(month_expenses),
    }, indent=2)


# ─── Monthly History & Rolling Average Helpers ──────────────────────────────


def _compute_monthly_history(expenses: list[dict], categories: list[str] | None = None) -> dict:
    """
    Compute per-month spending totals from all expense data.

    Returns:
        {
            "months": ["2026-01", "2026-02", "2026-03"],   # sorted ascending
            "totals": {"2026-01": 420.0, ...},              # overall per-month
            "by_category": {
                "food":  {"2026-01": 120.0, "2026-02": 130.0, ...},
                "bills": {"2026-01": 200.0, ...},
                ...
            }
        }
    """
    month_totals: dict[str, float] = defaultdict(float)
    month_by_cat: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for e in expenses:
        month_key = e["date"][:7]  # "YYYY-MM"
        month_totals[month_key] += e["amount"]
        month_by_cat[e["category"]][month_key] += e["amount"]

    sorted_months = sorted(month_totals.keys())

    # Fill in zeros for categories that have no spend in a given month
    if categories:
        for cat in categories:
            if cat not in month_by_cat:
                month_by_cat[cat] = {}
            for m in sorted_months:
                month_by_cat[cat].setdefault(m, 0.0)

    return {
        "months": sorted_months,
        "totals": {m: round(month_totals[m], 2) for m in sorted_months},
        "by_category": {
            cat: {m: round(vals.get(m, 0), 2) for m in sorted_months}
            for cat, vals in month_by_cat.items()
        },
    }


def _compute_rolling_average(monthly_values: list[float], window: int = 3) -> list[float | None]:
    """
    Compute a rolling average over *window* periods.
    Returns a list the same length as input. Positions with insufficient
    history are None (not enough data for a full window).
    For the first data point, the value itself is returned so charts always
    have something to show.
    """
    result: list[float | None] = []
    for i in range(len(monthly_values)):
        if i == 0:
            # Always show first month's value (it's its own "average")
            result.append(round(monthly_values[0], 2))
        elif i < window - 1:
            # Partial window — use all available months so far
            avg = sum(monthly_values[: i + 1]) / (i + 1)
            result.append(round(avg, 2))
        else:
            avg = sum(monthly_values[i - window + 1 : i + 1]) / window
            result.append(round(avg, 2))
    return result


# ─── Tool 3: Predict Month-End Spending ──────────────────────────────────────


@tool("predict_month_end_spending")
def predict_month_end_spending(category: str) -> str:
    """
    Project end-of-month total spending for a category based on current burn rate.
    Args:
        category: Expense category (food, transport, entertainment, bills, healthcare)
    Returns:
        JSON string with projected total, daily burn rate, and budget comparison.
    """
    profile = _load_user_profile()
    expenses = _load_expenses()

    budget_limit = profile["budget_limits"].get(category, 0)

    month_start_str, days_in_month, days_elapsed = _get_latest_month(expenses)
    days_elapsed = max(days_elapsed, 1)

    month_expenses = [
        e for e in expenses
        if e["category"] == category
        and e["date"] >= month_start_str
    ]
    total_spent = sum(e["amount"] for e in month_expenses)

    daily_burn_rate = total_spent / days_elapsed
    projected_total = daily_burn_rate * days_in_month
    projected_vs_budget = projected_total - budget_limit

    if projected_total > budget_limit:
        forecast = "WILL_EXCEED_BUDGET"
    elif projected_total > budget_limit * 0.8:
        forecast = "AT_RISK"
    else:
        forecast = "WITHIN_BUDGET"

    # 3-month rolling average for this category
    history = _compute_monthly_history(expenses, [category])
    cat_monthly_vals = [history["by_category"].get(category, {}).get(m, 0) for m in history["months"]]
    rolling_avg = _compute_rolling_average(cat_monthly_vals)
    current_rolling_avg = rolling_avg[-1] if rolling_avg else None

    # Trend direction
    if len(rolling_avg) >= 2 and rolling_avg[-1] is not None and rolling_avg[-2] is not None:
        diff = rolling_avg[-1] - rolling_avg[-2]
        if diff > 5:
            trend = "INCREASING"
        elif diff < -5:
            trend = "DECREASING"
        else:
            trend = "STABLE"
    else:
        trend = "INSUFFICIENT_DATA"

    return json.dumps({
        "category": category,
        "current_total": round(total_spent, 2),
        "days_elapsed": days_elapsed,
        "days_in_month": days_in_month,
        "daily_burn_rate": round(daily_burn_rate, 2),
        "projected_month_end_total": round(projected_total, 2),
        "budget_limit": budget_limit,
        "projected_over_under": round(projected_vs_budget, 2),
        "forecast": forecast,
        "rolling_avg_3m": current_rolling_avg,
        "trend": trend,
        "monthly_history": {
            "months": history["months"],
            "values": cat_monthly_vals,
            "rolling_avg": rolling_avg,
        },
    }, indent=2)


# ─── Recurring Transaction Detection ─────────────────────────────────────────


def _normalize_description(desc: str) -> str:
    """
    Normalize a transaction description for fuzzy matching.
    Strips numbers, extra whitespace, lowercases — so that
    "Electricity bill payment" and "Electricity Bill" match.
    """
    text = desc.lower().strip()
    # Remove trailing amounts / reference numbers like "#12345" or "$120"
    text = re.sub(r"[#$]\d+[\.\d]*", "", text)
    # Remove standalone numbers (dates, ids) but keep words with digits
    text = re.sub(r"\b\d+\b", "", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _detect_recurring(expenses: list[dict], amount_tolerance: float = 0.20, day_tolerance: int = 5) -> list[dict]:
    """
    Detect recurring / subscription-like transactions.

    Algorithm:
    1. Group transactions by (normalized description, category).
    2. Within each group, check if transactions appear on similar days
       of the month (within day_tolerance) AND have similar amounts
       (within amount_tolerance fraction).
    3. If a group has >= 2 matches it's flagged as recurring.

    Also catches single-month subscriptions if the description contains
    subscription-related keywords.

    Returns a list of recurring-spend dicts.
    """
    SUBSCRIPTION_KEYWORDS = {
        "subscription", "monthly", "recurring", "autopay", "auto-pay",
        "premium", "membership", "plan", "renewal", "bill", "emi",
        "installment", "insurance", "rent", "netflix", "spotify",
        "internet", "mobile phone", "utilities",
    }

    # Group by (normalised description, category)
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for e in expenses:
        key = (_normalize_description(e["description"]), e["category"])
        groups[key].append(e)

    recurring: list[dict] = []
    seen_keys: set[tuple[str, str]] = set()

    for (norm_desc, category), txns in groups.items():
        if len(txns) < 2:
            # Single transaction — only flag if it looks like a subscription
            if len(txns) == 1:
                desc_lower = txns[0]["description"].lower()
                if any(kw in desc_lower for kw in SUBSCRIPTION_KEYWORDS):
                    t = txns[0]
                    recurring.append({
                        "description": t["description"],
                        "category": category,
                        "amount": t["amount"],
                        "frequency": "likely_monthly",
                        "confidence": "medium",
                        "occurrences": 1,
                        "dates": [t["date"]],
                        "monthly_cost": round(t["amount"], 2),
                        "detected_by": "keyword",
                    })
                    seen_keys.add((norm_desc, category))
            continue

        # Sort by date
        txns_sorted = sorted(txns, key=lambda x: x["date"])

        # Check amount similarity — all amounts within tolerance of the median
        amounts = [t["amount"] for t in txns_sorted]
        median_amount = sorted(amounts)[len(amounts) // 2]

        similar_amount_txns = [
            t for t in txns_sorted
            if abs(t["amount"] - median_amount) <= median_amount * amount_tolerance
        ]

        if len(similar_amount_txns) < 2:
            continue

        # Check day-of-month clustering
        days_of_month = [datetime.strptime(t["date"], "%Y-%m-%d").day for t in similar_amount_txns]
        median_day = sorted(days_of_month)[len(days_of_month) // 2]
        clustered = [
            t for i, t in enumerate(similar_amount_txns)
            if abs(days_of_month[i] - median_day) <= day_tolerance
        ]

        if len(clustered) >= 2:
            avg_amount = round(sum(t["amount"] for t in clustered) / len(clustered), 2)
            recurring.append({
                "description": clustered[0]["description"],
                "category": category,
                "amount": avg_amount,
                "frequency": "monthly",
                "confidence": "high" if len(clustered) >= 3 else "medium",
                "occurrences": len(clustered),
                "dates": [t["date"] for t in clustered],
                "day_of_month": median_day,
                "monthly_cost": avg_amount,
                "detected_by": "pattern",
            })
            seen_keys.add((norm_desc, category))
        # If not clustered by day but amounts match — might be recurring at irregular interval
        elif len(similar_amount_txns) >= 2:
            desc_lower = similar_amount_txns[0]["description"].lower()
            if any(kw in desc_lower for kw in SUBSCRIPTION_KEYWORDS):
                avg_amount = round(sum(t["amount"] for t in similar_amount_txns) / len(similar_amount_txns), 2)
                recurring.append({
                    "description": similar_amount_txns[0]["description"],
                    "category": category,
                    "amount": avg_amount,
                    "frequency": "likely_monthly",
                    "confidence": "medium",
                    "occurrences": len(similar_amount_txns),
                    "dates": [t["date"] for t in similar_amount_txns],
                    "monthly_cost": avg_amount,
                    "detected_by": "keyword+amount",
                })
                seen_keys.add((norm_desc, category))

    # Sort by monthly cost descending
    recurring.sort(key=lambda r: r["monthly_cost"], reverse=True)
    return recurring


# ─── Tool 4a: Detect Recurring Transactions ─────────────────────────────────


@tool("detect_recurring_transactions")
def detect_recurring_transactions(scope: str) -> str:
    """
    Detect recurring or subscription-like transactions (bills, EMIs, subscriptions).
    Groups transactions by description similarity and flags those appearing on
    similar days each month with similar amounts.
    Args:
        scope: 'all' to scan everything, or a category name like 'bills'.
    Returns:
        JSON string with detected recurring transactions, committed monthly total,
        and a breakdown of committed vs discretionary spending.
    """
    expenses = _load_expenses()
    profile = _load_user_profile()

    if scope != "all":
        expenses = [e for e in expenses if e["category"] == scope]

    recurring = _detect_recurring(expenses)

    committed_total = sum(r["monthly_cost"] for r in recurring)
    total_spent = sum(e["amount"] for e in expenses)
    discretionary_total = round(total_spent - committed_total, 2)
    income = profile.get("monthly_income", 0)

    return json.dumps({
        "scope": scope,
        "recurring_count": len(recurring),
        "committed_monthly_total": round(committed_total, 2),
        "discretionary_total": discretionary_total,
        "total_spent": round(total_spent, 2),
        "monthly_income": income,
        "committed_percentage": round(committed_total / income * 100, 1) if income > 0 else 0,
        "discretionary_percentage": round(discretionary_total / income * 100, 1) if income > 0 else 0,
        "recurring_transactions": recurring,
    }, indent=2)


# ─── Tool 4b: Find Savings Opportunities ────────────────────────────────────


@tool("find_savings_opportunities")
def find_savings_opportunities(spending_data: str) -> str:
    """
    Analyze spending patterns to identify potential savings opportunities.
    Args:
        spending_data: A keyword like 'all' to analyze all data, or a specific category name.
    Returns:
        JSON string with identified savings opportunities and recommendations.
    """
    expenses = _load_expenses()
    profile = _load_user_profile()

    if spending_data != "all":
        expenses = [e for e in expenses if e["category"] == spending_data]

    category_totals: dict[str, float] = {}
    category_counts: dict[str, int] = {}
    for e in expenses:
        cat = e["category"]
        category_totals[cat] = category_totals.get(cat, 0) + e["amount"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    opportunities = []
    budget_limits = profile["budget_limits"]

    for cat, total in category_totals.items():
        limit = budget_limits.get(cat, 0)
        if limit > 0:
            ratio = total / limit
            if ratio > 0.9:
                opportunities.append({
                    "category": cat,
                    "type": "overspending",
                    "current_total": round(total, 2),
                    "budget_limit": limit,
                    "potential_savings": round(total - limit * 0.7, 2),
                    "suggestion": f"Reduce {cat} spending by cutting non-essential items. "
                                  f"Target 70% of budget (${limit * 0.7:.2f}) to save ${total - limit * 0.7:.2f}.",
                })

    small_purchases = [e for e in expenses if e["amount"] < 25]
    if len(small_purchases) > 5:
        small_total = sum(e["amount"] for e in small_purchases)
        opportunities.append({
            "category": "multiple",
            "type": "frequent_small_purchases",
            "count": len(small_purchases),
            "total": round(small_total, 2),
            "suggestion": f"You have {len(small_purchases)} small purchases (< $25) totaling ${small_total:.2f}. "
                          f"Consolidating or reducing these could save ~${small_total * 0.3:.2f}/month.",
        })

    entertainment_total = category_totals.get("entertainment", 0)
    food_total = category_totals.get("food", 0)
    total_all = sum(category_totals.values())
    discretionary = entertainment_total + food_total
    if total_all > 0 and (discretionary / total_all) > 0.4:
        opportunities.append({
            "category": "food+entertainment",
            "type": "high_discretionary_spending",
            "discretionary_total": round(discretionary, 2),
            "percentage_of_total": round(discretionary / total_all * 100, 1),
            "suggestion": f"Discretionary spending (food + entertainment) is {discretionary / total_all * 100:.1f}% "
                          f"of total. Consider meal prepping and free entertainment options to reduce by 20%.",
        })

    # ─── Recurring / subscription detection ───────────────────────────
    recurring = _detect_recurring(expenses)
    committed_total = sum(r["monthly_cost"] for r in recurring)

    if recurring:
        opportunities.append({
            "category": "subscriptions",
            "type": "recurring_committed_spend",
            "count": len(recurring),
            "committed_total": round(committed_total, 2),
            "items": [
                {"description": r["description"], "amount": r["monthly_cost"], "confidence": r["confidence"]}
                for r in recurring
            ],
            "suggestion": f"You have {len(recurring)} recurring charges totaling ${committed_total:.2f}/mo. "
                          f"Review each subscription — canceling unused ones could free up budget.",
        })

    total_potential = sum(o.get("potential_savings", 0) for o in opportunities)

    return json.dumps({
        "analysis_scope": spending_data,
        "total_analyzed": round(sum(category_totals.values()), 2),
        "opportunities_found": len(opportunities),
        "total_potential_savings": round(total_potential, 2),
        "opportunities": opportunities,
        "recurring_spend": {
            "committed_total": round(committed_total, 2),
            "recurring_count": len(recurring),
            "recurring_transactions": recurring,
        },
    }, indent=2)


# ─── Tool 5: Generate Spending Report ────────────────────────────────────────


@tool("generate_spending_report")
def generate_spending_report(date_range: str) -> str:
    """
    Generate a comprehensive financial summary report for a given date range.
    Args:
        date_range: Date range as 'YYYY-MM-DD to YYYY-MM-DD' (e.g., '2026-03-01 to 2026-03-31')
    Returns:
        JSON string with full spending report including per-category breakdown, budget comparison, and trends.
    """
    expenses = _load_expenses()
    profile = _load_user_profile()

    parts = date_range.replace(" ", "").split("to")
    start_date = parts[0] if len(parts) >= 1 else "2026-03-01"
    end_date = parts[1] if len(parts) >= 2 else "2026-03-31"

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    filtered = [
        e for e in expenses
        if start <= datetime.strptime(e["date"], "%Y-%m-%d") <= end
    ]

    category_breakdown = {}
    for e in filtered:
        cat = e["category"]
        if cat not in category_breakdown:
            category_breakdown[cat] = {"total": 0, "count": 0, "transactions": []}
        category_breakdown[cat]["total"] += e["amount"]
        category_breakdown[cat]["count"] += 1
        category_breakdown[cat]["transactions"].append(e["description"])

    for cat in category_breakdown:
        category_breakdown[cat]["total"] = round(category_breakdown[cat]["total"], 2)

    grand_total = sum(cb["total"] for cb in category_breakdown.values())

    budget_limits = profile["budget_limits"]
    budget_comparison = {}
    for cat, data in category_breakdown.items():
        limit = budget_limits.get(cat, 0)
        budget_comparison[cat] = {
            "spent": data["total"],
            "budget": limit,
            "remaining": round(limit - data["total"], 2),
            "percentage_used": round(data["total"] / limit * 100, 1) if limit > 0 else 0,
        }

    sorted_expenses = sorted(filtered, key=lambda x: x["amount"], reverse=True)
    top_5 = sorted_expenses[:5]

    days = max((end - start).days + 1, 1)
    daily_average = grand_total / days

    return json.dumps({
        "report_period": {"start": start_date, "end": end_date, "days": days},
        "summary": {
            "total_spending": round(grand_total, 2),
            "daily_average": round(daily_average, 2),
            "transaction_count": len(filtered),
            "monthly_income": profile["monthly_income"],
            "savings_rate": round((1 - grand_total / profile["monthly_income"]) * 100, 1)
                if profile["monthly_income"] > 0 else 0,
        },
        "category_breakdown": category_breakdown,
        "budget_comparison": budget_comparison,
        "top_expenses": top_5,
    }, indent=2)
