"""
Financial Advisor Agent

Responsibilities:
- Provides personalized saving tips based on spending analysis
- Suggests realistic budget adjustments
- Gives proactive alerts when approaching limits

Patterns demonstrated: Planning, Hierarchical coordination
"""

from crewai import Agent, LLM

from tools.financial_tools import (
    check_budget_status,
    predict_month_end_spending,
    detect_recurring_transactions,
    find_savings_opportunities,
    generate_spending_report,
)


def create_financial_advisor_agent(llm: LLM) -> Agent:
    """Create and return the Financial Advisor Agent."""
    return Agent(
        role="Financial Advisor",
        goal="Provide actionable savings advice with specific dollar amounts. Alert on approaching limits.",
        backstory=(
            "Certified financial advisor. Use Planning pattern: gather data, then create step-by-step plan. "
            "Coordinate with other agents. Every suggestion must include specific dollar amounts and timelines. "
            "Never give generic advice."
        ),
        tools=[
            check_budget_status,
            predict_month_end_spending,
            detect_recurring_transactions,
            find_savings_opportunities,
            generate_spending_report,
        ],
        llm=llm,
        verbose=True,
        allow_delegation=True,
    )
