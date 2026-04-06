"""
Personal Finance Manager — Multi-Agent System
==============================================

Orchestrates 3 CrewAI agents (Expense Tracker, Budget Analyzer, Financial Advisor)
with shared memory, tool use, and multiple collaboration patterns:
  - Sequential execution (series pipeline)
  - Hierarchical coordination (Financial Advisor as manager)

Uses Groq LLM (Llama 3.3 70B) via LiteLLM.
"""

import json
import os
import sys
import time

import litellm
from dotenv import load_dotenv
from crewai import Crew, Task, Process, LLM

from agents import (
    create_expense_tracker_agent,
    create_budget_analyzer_agent,
    create_financial_advisor_agent,
)
from memory.memory_system import MemoryManager

# ─── Rate Limiter for Groq Free Tier (12K TPM) ──────────────────────────────
_original_completion = litellm.completion
_last_call_time = 0


def _rate_limited_completion(*args, **kwargs):
    global _last_call_time
    elapsed = time.time() - _last_call_time
    min_interval = 15
    if elapsed < min_interval:
        wait = min_interval - elapsed
        print(f"  [Rate limiter] Waiting {wait:.0f}s for Groq rate limit...")
        time.sleep(wait)
    _last_call_time = time.time()
    return _original_completion(*args, **kwargs)


litellm.completion = _rate_limited_completion
litellm.num_retries = 5
litellm.retry_after = 20


# ─── Lazy Initialization ─────────────────────────────────────────────────────

_initialized = False
_llm = None
_expense_tracker = None
_budget_analyzer = None
_financial_advisor = None
_memory_context = ""


def initialize():
    """Initialize LLM, agents, and memory context. Safe to call multiple times."""
    global _initialized, _llm, _expense_tracker, _budget_analyzer, _financial_advisor, _memory_context

    if _initialized:
        return

    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set in .env file")

    _llm = LLM(
        model="groq/llama-3.3-70b-versatile",
        api_key=api_key,
        temperature=0.3,
        max_tokens=1024,
    )

    _expense_tracker = create_expense_tracker_agent(_llm)
    _budget_analyzer = create_budget_analyzer_agent(_llm)
    _financial_advisor = create_financial_advisor_agent(_llm)

    # Use MemoryManager — will use DB if in app context, else JSON fallback
    mm = MemoryManager()
    ctx = mm.get_full_context()
    _memory_context = (
        f"Income: ${ctx['monthly_income']:.0f}/mo. "
        f"Budgets: food=$400, transport=$200, entertainment=$250, bills=$600, healthcare=$300. "
        f"Goals: Emergency Fund $10K by Dec 2026 (have $3.5K), Vacation $3K by Aug 2026 (have $800)."
    )

    _initialized = True
    print("CrewAI agents initialized.")


# ─── Collaboration Patterns ──────────────────────────────────────────────────


def run_sequential():
    """
    Pattern 1: Sequential Execution (Series Pipeline)
    Expense Tracker -> Budget Analyzer -> Financial Advisor
    """
    initialize()

    task_track = Task(
        description=(
            f"{_memory_context}\n"
            "Analyze March 2026 expenses. Use generate_spending_report with "
            "date_range='2026-03-01 to 2026-03-31'. "
            "Then summarize total per category and flag unusual spending (any single "
            "transaction > 50% of its category budget). Be concise."
        ),
        expected_output="Expense summary: total per category, transaction counts, flagged anomalies.",
        agent=_expense_tracker,
    )

    task_budget = Task(
        description=(
            f"{_memory_context}\n"
            "Check budget status for all 5 categories using check_budget_status tool. "
            "For any category above 70% usage, use predict_month_end_spending. "
            "Reflect: double-check your analysis for accuracy. Prioritize concerns."
        ),
        expected_output="Budget status per category with percentage used, remaining, month-end projections.",
        agent=_budget_analyzer,
    )

    task_advise = Task(
        description=(
            f"{_memory_context}\n"
            "Based on the expense and budget analysis above, use find_savings_opportunities "
            "with spending_data='all'. Then provide: top 3 savings tips with dollar amounts, "
            "budget adjustment suggestions, and goal progress assessment."
        ),
        expected_output="Financial advice: savings, budget adjustments, goal progress, action plan.",
        agent=_financial_advisor,
    )

    crew = Crew(
        agents=[_expense_tracker, _budget_analyzer, _financial_advisor],
        tasks=[task_track, task_budget, task_advise],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    return result


def run_hierarchical():
    """
    Pattern 2: Hierarchical Coordination
    Financial Advisor coordinates the full review.
    """
    initialize()

    manager_task = Task(
        description=(
            f"{_memory_context}\n"
            "You are the lead Financial Advisor. Do a full financial review:\n"
            "1. Use generate_spending_report for '2026-03-01 to 2026-03-31'\n"
            "2. Use check_budget_status for each category\n"
            "3. Use find_savings_opportunities with spending_data='all'\n"
            "4. Synthesize into a financial health report with actionable advice."
        ),
        expected_output="Comprehensive report: spending, budget status, savings, goal progress, action items.",
        agent=_financial_advisor,
    )

    crew = Crew(
        agents=[_financial_advisor, _expense_tracker, _budget_analyzer],
        tasks=[manager_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    return result


# ─── CLI Entry Point ─────────────────────────────────────────────────────────


def main():
    initialize()
    mm = MemoryManager()

    print("=" * 70)
    print("   PERSONAL FINANCE MANAGER — MULTI-AGENT SYSTEM")
    print("   Powered by CrewAI + Groq (Llama 3.3 70B)")
    print("=" * 70)
    print()
    print(f"  Transactions: {len(mm.long_term.spending_history)}")
    print(f"  Monthly income: ${mm.long_term.get_monthly_income():,.2f}")
    print()

    print("Checking budget alerts...")
    alerts = []
    for category in mm.long_term.get_budget_limits():
        alert = mm.check_budget_alert(category)
        if alert:
            alerts.append(alert)
            print(f"  ! {alert['message']}")
    if not alerts:
        print("  No budget alerts at this time.")
    print()

    print("Select workflow pattern:")
    print("  1. Sequential (Expense Tracker -> Budget Analyzer -> Financial Advisor)")
    print("  2. Hierarchical (Financial Advisor coordinates all agents)")
    print("  3. Run both patterns")
    print()

    choice = input("Enter choice (1/2/3): ").strip()

    if choice == "1":
        result = run_sequential()
        print("\n" + "=" * 70)
        print("FINAL RESULT - Sequential Workflow")
        print("=" * 70)
        print(result)
    elif choice == "2":
        result = run_hierarchical()
        print("\n" + "=" * 70)
        print("FINAL RESULT - Hierarchical Workflow")
        print("=" * 70)
        print(result)
    elif choice == "3":
        result1 = run_sequential()
        print("\nWaiting 60s for rate limit cooldown...\n")
        time.sleep(60)
        result2 = run_hierarchical()
        print("\n" + "=" * 70)
        print("FINAL RESULTS")
        print("=" * 70)
        print("\n[Sequential Result]")
        print(result1)
        print("\n[Hierarchical Result]")
        print(result2)
    else:
        print("Invalid choice. Running sequential by default.")
        result = run_sequential()
        print(result)

    mm.save_all()
    print("\nMemory saved successfully.")


if __name__ == "__main__":
    main()
