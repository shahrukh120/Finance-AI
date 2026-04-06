"""
Tests for the 5 Financial Tools.
Run with: python -m pytest tests/ -v
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.financial_tools import (
    calculate_category_total,
    check_budget_status,
    predict_month_end_spending,
    detect_recurring_transactions,
    find_savings_opportunities,
    generate_spending_report,
    _detect_recurring,
    _normalize_description,
    _compute_monthly_history,
    _compute_rolling_average,
)


class TestCalculateCategoryTotal:
    def test_food_category(self):
        result = json.loads(calculate_category_total.run(
            category="food", start_date="2026-03-01", end_date="2026-03-31"
        ))
        assert result["category"] == "food"
        assert result["total_amount"] > 0
        assert result["transaction_count"] > 0

    def test_empty_date_range(self):
        result = json.loads(calculate_category_total.run(
            category="food", start_date="2025-01-01", end_date="2025-01-31"
        ))
        assert result["total_amount"] == 0
        assert result["transaction_count"] == 0

    def test_all_categories_have_data(self):
        for cat in ["food", "transport", "entertainment", "bills", "healthcare"]:
            result = json.loads(calculate_category_total.run(
                category=cat, start_date="2026-03-01", end_date="2026-03-31"
            ))
            assert result["transaction_count"] > 0, f"No transactions for {cat}"


class TestCheckBudgetStatus:
    def test_returns_valid_status(self):
        result = json.loads(check_budget_status.run(category="food"))
        assert result["category"] == "food"
        assert result["budget_limit"] > 0
        assert result["status"] in ["HEALTHY", "ON_TRACK", "WARNING", "OVER_BUDGET"]
        assert "percentage_used" in result

    def test_all_categories(self):
        for cat in ["food", "transport", "entertainment", "bills", "healthcare"]:
            result = json.loads(check_budget_status.run(category=cat))
            assert result["budget_limit"] > 0


class TestPredictMonthEndSpending:
    def test_returns_projection(self):
        result = json.loads(predict_month_end_spending.run(category="food"))
        assert result["category"] == "food"
        assert "projected_month_end_total" in result
        assert "daily_burn_rate" in result
        assert result["forecast"] in ["WITHIN_BUDGET", "AT_RISK", "WILL_EXCEED_BUDGET"]

    def test_days_in_month_positive(self):
        result = json.loads(predict_month_end_spending.run(category="bills"))
        assert result["days_in_month"] > 0
        assert result["days_elapsed"] > 0


class TestNormalizeDescription:
    def test_basic_normalization(self):
        assert _normalize_description("Electricity Bill Payment") == "electricity bill payment"

    def test_strips_amounts(self):
        assert "$" not in _normalize_description("Payment $120.00")

    def test_strips_reference_numbers(self):
        assert "#" not in _normalize_description("Order #12345")

    def test_collapses_whitespace(self):
        result = _normalize_description("  too   many   spaces  ")
        assert "  " not in result


class TestDetectRecurring:
    def test_detects_similar_transactions(self):
        """Two transactions with same description, similar amount should be flagged."""
        expenses = [
            {"id": 1, "date": "2026-02-10", "category": "bills", "amount": 85.0, "description": "Internet bill"},
            {"id": 2, "date": "2026-03-10", "category": "bills", "amount": 85.0, "description": "Internet bill"},
        ]
        result = _detect_recurring(expenses)
        assert len(result) >= 1
        assert result[0]["monthly_cost"] == 85.0
        assert result[0]["category"] == "bills"

    def test_detects_subscription_keywords(self):
        """Single transaction with subscription keyword should be flagged."""
        expenses = [
            {"id": 1, "date": "2026-03-15", "category": "entertainment", "amount": 35.0,
             "description": "Netflix and Spotify subscription"},
        ]
        result = _detect_recurring(expenses)
        assert len(result) >= 1
        assert result[0]["detected_by"] == "keyword"

    def test_ignores_dissimilar_amounts(self):
        """Same description but wildly different amounts should not match."""
        expenses = [
            {"id": 1, "date": "2026-02-05", "category": "food", "amount": 10.0, "description": "Grocery shopping"},
            {"id": 2, "date": "2026-03-05", "category": "food", "amount": 200.0, "description": "Grocery shopping"},
        ]
        result = _detect_recurring(expenses)
        # Should NOT be flagged as recurring (amounts differ > 20%)
        assert len(result) == 0

    def test_empty_expenses(self):
        assert _detect_recurring([]) == []


class TestDetectRecurringTransactionsTool:
    def test_all_scope(self):
        result = json.loads(detect_recurring_transactions.run(scope="all"))
        assert "recurring_count" in result
        assert "committed_monthly_total" in result
        assert "discretionary_total" in result
        assert "recurring_transactions" in result
        assert isinstance(result["recurring_transactions"], list)

    def test_category_scope(self):
        result = json.loads(detect_recurring_transactions.run(scope="bills"))
        assert result["scope"] == "bills"
        assert "committed_monthly_total" in result

    def test_committed_percentage(self):
        result = json.loads(detect_recurring_transactions.run(scope="all"))
        assert "committed_percentage" in result
        assert "discretionary_percentage" in result
        assert result["monthly_income"] > 0


class TestFindSavingsOpportunities:
    def test_analyze_all(self):
        result = json.loads(find_savings_opportunities.run(spending_data="all"))
        assert "opportunities" in result
        assert "total_analyzed" in result
        assert result["total_analyzed"] > 0

    def test_single_category(self):
        result = json.loads(find_savings_opportunities.run(spending_data="food"))
        assert result["analysis_scope"] == "food"

    def test_includes_recurring_spend(self):
        result = json.loads(find_savings_opportunities.run(spending_data="all"))
        assert "recurring_spend" in result
        assert "committed_total" in result["recurring_spend"]
        assert "recurring_count" in result["recurring_spend"]
        assert "recurring_transactions" in result["recurring_spend"]


class TestGenerateSpendingReport:
    def test_march_report(self):
        result = json.loads(generate_spending_report.run(
            date_range="2026-03-01 to 2026-03-31"
        ))
        assert result["report_period"]["start"] == "2026-03-01"
        assert result["report_period"]["end"] == "2026-03-31"
        assert result["summary"]["total_spending"] > 0
        assert result["summary"]["transaction_count"] > 0
        assert "category_breakdown" in result
        assert "budget_comparison" in result
        assert "top_expenses" in result

    def test_report_has_all_categories(self):
        result = json.loads(generate_spending_report.run(
            date_range="2026-03-01 to 2026-03-31"
        ))
        for cat in ["food", "transport", "entertainment", "bills", "healthcare"]:
            assert cat in result["category_breakdown"], f"Missing category: {cat}"


class TestComputeMonthlyHistory:
    def test_groups_by_month(self):
        expenses = [
            {"date": "2026-01-05", "category": "food", "amount": 50.0},
            {"date": "2026-01-20", "category": "food", "amount": 30.0},
            {"date": "2026-02-10", "category": "food", "amount": 40.0},
        ]
        result = _compute_monthly_history(expenses)
        assert result["months"] == ["2026-01", "2026-02"]
        assert result["totals"]["2026-01"] == 80.0
        assert result["totals"]["2026-02"] == 40.0

    def test_by_category_breakdown(self):
        expenses = [
            {"date": "2026-03-01", "category": "food", "amount": 100.0},
            {"date": "2026-03-15", "category": "bills", "amount": 200.0},
        ]
        result = _compute_monthly_history(expenses, ["food", "bills"])
        assert result["by_category"]["food"]["2026-03"] == 100.0
        assert result["by_category"]["bills"]["2026-03"] == 200.0

    def test_fills_zeros_for_missing_categories(self):
        expenses = [
            {"date": "2026-01-10", "category": "food", "amount": 50.0},
        ]
        result = _compute_monthly_history(expenses, ["food", "transport"])
        assert result["by_category"]["transport"]["2026-01"] == 0.0

    def test_empty_expenses(self):
        result = _compute_monthly_history([])
        assert result["months"] == []
        assert result["totals"] == {}

    def test_multiple_months_sorted(self):
        expenses = [
            {"date": "2026-03-01", "category": "food", "amount": 30.0},
            {"date": "2026-01-01", "category": "food", "amount": 10.0},
            {"date": "2026-02-01", "category": "food", "amount": 20.0},
        ]
        result = _compute_monthly_history(expenses)
        assert result["months"] == ["2026-01", "2026-02", "2026-03"]


class TestComputeRollingAverage:
    def test_single_value(self):
        result = _compute_rolling_average([100.0])
        assert result == [100.0]

    def test_two_values(self):
        result = _compute_rolling_average([100.0, 200.0])
        assert result[0] == 100.0
        assert result[1] == 150.0  # avg of 100, 200

    def test_three_values_window_3(self):
        result = _compute_rolling_average([100.0, 200.0, 300.0], window=3)
        assert result[0] == 100.0
        assert result[1] == 150.0   # partial: (100+200)/2
        assert result[2] == 200.0   # full: (100+200+300)/3

    def test_four_values_window_3(self):
        result = _compute_rolling_average([100.0, 200.0, 300.0, 400.0], window=3)
        assert result[3] == 300.0  # (200+300+400)/3

    def test_empty_list(self):
        result = _compute_rolling_average([])
        assert result == []

    def test_values_are_rounded(self):
        result = _compute_rolling_average([10.0, 20.0, 33.0], window=3)
        assert result[2] == 21.0  # (10+20+33)/3 = 21.0


class TestPredictMonthEndSpendingTrend:
    def test_includes_rolling_avg(self):
        result = json.loads(predict_month_end_spending.run(category="food"))
        assert "rolling_avg_3m" in result
        assert "trend" in result
        assert result["trend"] in ["INCREASING", "DECREASING", "STABLE", "INSUFFICIENT_DATA"]

    def test_includes_monthly_history(self):
        result = json.loads(predict_month_end_spending.run(category="food"))
        assert "monthly_history" in result
        history = result["monthly_history"]
        assert "months" in history
        assert "values" in history
        assert "rolling_avg" in history
        assert len(history["months"]) == len(history["values"])
        assert len(history["months"]) == len(history["rolling_avg"])
