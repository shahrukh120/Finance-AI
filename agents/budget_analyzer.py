"""
Budget Analyzer Agent

Responsibilities:
- Compares actual spending vs budget limits
- Identifies overspending categories
- Calculates remaining budget and burn rate

Patterns demonstrated: ReAct, Reflection
"""

from crewai import Agent, LLM

from tools.financial_tools import (
    check_budget_status,
    predict_month_end_spending,
    generate_spending_report,
)


def create_budget_analyzer_agent(llm: LLM) -> Agent:
    """Create and return the Budget Analyzer Agent."""
    return Agent(
        role="Budget Analyzer",
        goal="Compare spending vs budget limits. Identify overspending and calculate burn rates.",
        backstory=(
            "Budget management expert. Compare spending against limits category by category. "
            "Use Reflection pattern: analyze first, then re-examine conclusions for accuracy. "
            "Always provide specific numbers and data-driven insights."
        ),
        tools=[check_budget_status, predict_month_end_spending, generate_spending_report],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
