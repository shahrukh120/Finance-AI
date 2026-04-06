"""
Expense Tracker Agent

Responsibilities:
- Records daily expenses with categories (food, transport, entertainment, bills, healthcare)
- Calculates total spending per category and period
- Identifies unusual spending patterns

Patterns demonstrated: ReAct (Reason + Act), Planning
"""

from crewai import Agent, LLM

from tools.financial_tools import (
    calculate_category_total,
    check_budget_status,
    generate_spending_report,
)


def create_expense_tracker_agent(llm: LLM) -> Agent:
    """Create and return the Expense Tracker Agent."""
    return Agent(
        role="Expense Tracker",
        goal="Track and analyze expenses by category. Flag unusual spending patterns.",
        backstory=(
            "Expert financial record-keeper. Categories: food, transport, entertainment, bills, healthcare. "
            "Flag anomalies like single purchases exceeding 50% of category budget. Use ReAct pattern: "
            "Reason about what to do, Act by calling a tool, Observe the result."
        ),
        tools=[calculate_category_total, check_budget_status, generate_spending_report],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
